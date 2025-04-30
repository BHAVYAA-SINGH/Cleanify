# waste_management/models.py
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Avg
import logging

logger = logging.getLogger(__name__)

# --- Choices ---

ROLE_CHOICES = (
    ('Requestee', 'Requestee'),
    ('Worker', 'Worker'),
)

CATEGORY_CHOICES = (
    ('Garbage Collection', 'Garbage Collection'),
    ('Water Leakage', 'Water Leakage'),
    ('Washroom Cleaning', 'Washroom Cleaning'),
    ('Electricity Issue', 'Electricity Issue'),
)

STATUS_CHOICES = (
    ('Pending', 'Pending'),
    ('Assigned', 'Assigned'),
    ('Pending Approval', 'Pending Approval'),
    ('Completed', 'Completed'),
)

RATING_CHOICES = (
    (1, '1 - Poor'),
    (2, '2 - Fair'),
    (3, '3 - Good'),
    (4, '4 - Very Good'),
    (5, '5 - Excellent'),
)

# --- Models ---

class UserProfile(models.Model):
    """ Extends User: Role, Worker Category, Avg Rating, Busy Status """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, blank=False, null=False)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, null=True, blank=True)
    average_rating = models.FloatField(null=True, blank=True, default=None)
    is_busy = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    def save(self, *args, **kwargs):
        if self.role != 'Worker':
            self.category = None
            self.average_rating = None
            self.is_busy = False
        elif self.role == 'Worker' and not self.category:
            logger.warning(f"Worker profile saved without category for user: {self.user.username}")
        super().save(*args, **kwargs)

    def update_average_rating(self):
        """ Calculates and updates the worker's average rating based on ALL submitted ratings. """
        if self.role != 'Worker':
            logger.warning(f"Attempted to update rating for non-worker: {self.user.username}")
            return # Should not happen if called correctly

        try:
            # Filter ALL requests ever assigned to this worker that have received a rating
            requests_rated = WasteRequest.objects.filter(
                assigned_worker=self.user,
                worker_rating__isnull=False # Ensure rating exists
            )
            count = requests_rated.count()
            logger.debug(f"Found {count} rated requests for worker {self.user.username}")

            # Calculate average ONLY if there are rated requests
            if count > 0:
                aggregation_result = requests_rated.aggregate(Avg('worker_rating'))
                avg_rating_value = aggregation_result.get('worker_rating__avg') # Use .get for safety
                logger.debug(f"Calculated avg rating value for {self.user.username}: {avg_rating_value}")

                if avg_rating_value is not None:
                    self.average_rating = round(avg_rating_value, 2)
                else:
                    # This case should ideally not happen if count > 0 and ratings are integers
                    logger.warning(f"Avg calculation returned None despite {count} rated requests for {self.user.username}.")
                    self.average_rating = None
            else:
                # No rated requests found, set average rating to None
                self.average_rating = None
                logger.debug(f"No rated requests found for {self.user.username}, setting average rating to None.")

            # Save the updated rating (or None)
            self.save(update_fields=['average_rating'])
            logger.info(f"Successfully updated average rating for worker {self.user.username} to {self.average_rating}")

        except Exception as e:
            logger.error(f"CRITICAL error updating average rating for worker {self.user.username}: {e}", exc_info=True)


    def update_busy_status(self):
        """ Checks if the worker has any 'Assigned' tasks and updates is_busy flag. """
        if self.role != 'Worker':
            if self.is_busy: # If somehow a non-worker was marked busy, correct it
                 self.is_busy = False
                 self.save(update_fields=['is_busy'])
            return

        try:
            is_currently_assigned = WasteRequest.objects.filter(
                assigned_worker=self.user,
                status='Assigned'
            ).exists()

            # Update only if the status changed
            if self.is_busy != is_currently_assigned:
                self.is_busy = is_currently_assigned
                self.save(update_fields=['is_busy'])
                logger.debug(f"Updated busy status for worker {self.user.username} to {self.is_busy}")
            else:
                 logger.debug(f"Busy status for worker {self.user.username} unchanged ({self.is_busy}).")
        except Exception as e:
             logger.error(f"Error updating busy status for worker {self.user.username}: {e}", exc_info=True)


class WasteRequest(models.Model):
    """ Represents a waste management or service request. """
    requestee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_requests')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, blank=False, null=False)
    location = models.CharField(max_length=255, blank=False, null=False)
    description = models.TextField(blank=True, null=True)
    request_image = models.ImageField(upload_to='request_images/', blank=False, null=False)
    completion_image = models.ImageField(upload_to='completion_images/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_worker = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='assigned_tasks', null=True, blank=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    is_approved_by_student = models.BooleanField(default=False) # Renamed to is_approved_by_requestee if needed? Stick to student for now
    worker_rating = models.IntegerField(choices=RATING_CHOICES, null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        rating_info = f", Rated: {self.get_worker_rating_display()}" if self.worker_rating else ""
        worker_info = f", Worker: {self.assigned_worker.username}" if self.assigned_worker else ""
        approval_info = f", Approved: {self.is_approved_by_student}" if self.status == 'Completed' else ""
        return f"ID:{self.id} Req by {self.requestee.username} ({self.status}{worker_info}{rating_info}{approval_info})"