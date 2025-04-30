# waste_management/views.py

# --- Django & Python Imports ---
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm # Keep these standard imports
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
import logging

# --- App Imports ---
from .models import WasteRequest, UserProfile # Import correct models
from .forms import (
    CustomUserCreationForm,
    RequestCreationForm,
    WorkerCompletionForm,
    ApprovalRatingForm,
    AdminManualAssignForm
)

# Get logger instance
logger = logging.getLogger(__name__)

# =======================================
# === DECORATORS (Defined here for simplicity) ===
# =======================================

def requestee_required(function=None, login_url='login'):
    """ Decorator for views that require Requestee role via UserProfile. """
    actual_decorator = user_passes_test(
            lambda u: u.is_authenticated and hasattr(u, 'profile') and u.profile.role == 'Requestee',
            login_url=login_url
        )
    if function: return actual_decorator(function)
    return actual_decorator

def worker_required(function=None, login_url='login'):
    """ Decorator for views that require Worker role via UserProfile. """
    actual_decorator = user_passes_test(
            lambda u: u.is_authenticated and hasattr(u, 'profile') and u.profile.role == 'Worker',
            login_url=login_url
        )
    if function: return actual_decorator(function)
    return actual_decorator

def admin_required(function=None, login_url='login'):
    """ Decorator for views that require Admin/Staff status. """
    actual_decorator = user_passes_test(
            lambda u: u.is_active and (u.is_staff or u.is_superuser),
            login_url=login_url
        )
    if function: return actual_decorator(function)
    return actual_decorator

# =======================================
# === HELPER FUNCTION: AUTO-ASSIGNMENT ===
# =======================================
# (find_and_assign_worker and try_assign_pending_task_to_worker remain the same as previous response)
def find_and_assign_worker(request_instance):
    """
    Tries to find a *free* worker of the *matching category* and assign the request.
    Returns True if assigned, False otherwise. Uses UserProfile.
    """
    category = request_instance.category
    logger.debug(f"Attempting auto-assignment for Request ID: {request_instance.id}, Category: {category}")
    available_workers = User.objects.filter(
        profile__role='Worker',
        profile__category=category,
        profile__is_busy=False,
        is_active=True
    ).order_by('?')
    worker_to_assign = available_workers.first()
    if worker_to_assign:
        request_instance.assigned_worker = worker_to_assign
        request_instance.assigned_at = timezone.now()
        request_instance.status = 'Assigned'
        request_instance.save(update_fields=['assigned_worker', 'assigned_at', 'status'])
        try:
            worker_profile = worker_to_assign.profile
            worker_profile.is_busy = True
            worker_profile.save(update_fields=['is_busy'])
        except UserProfile.DoesNotExist:
             logger.error(f"UserProfile not found for assigned worker {worker_to_assign.username} during auto-assignment!")
             pass
        logger.info(f"Auto-assigned Request ID: {request_instance.id} to Worker: {worker_to_assign.username}")
        return True
    else:
        logger.info(f"No free worker found for Request ID: {request_instance.id} (Category: {category}). Status remains Pending.")
        if request_instance.status != 'Pending':
             request_instance.status = 'Pending'
             request_instance.save(update_fields=['status'])
        return False

def try_assign_pending_task_to_worker(worker):
    """
    Checks if there are pending tasks matching the worker's category
    and assigns the oldest one if the worker is free. Uses UserProfile.
    """
    if not worker or not hasattr(worker, 'profile') or worker.profile.role != 'Worker':
        logger.warning(f"Attempted to assign task to non-worker or user without profile: {worker}")
        return
    worker.profile.refresh_from_db()
    if worker.profile.is_busy:
        logger.debug(f"Worker {worker.username} is busy, skipping pending task check.")
        return
    category = worker.profile.category
    if not category:
         logger.warning(f"Worker {worker.username} has no category, cannot assign tasks.")
         return
    logger.debug(f"Checking for pending tasks for free Worker: {worker.username}, Cat: {category}")
    pending_request = WasteRequest.objects.filter(
        status='Pending', category=category
    ).order_by('created_at').first()
    if pending_request:
        logger.info(f"Found pending Request ID: {pending_request.id} for Worker: {worker.username}.")
        find_and_assign_worker(pending_request)
    else:
        logger.debug(f"No pending tasks found for Cat: {category} for Worker: {worker.username}")

# =======================================
# === AUTHENTICATION & STATIC VIEWS ===
# =======================================
# (landing_page, about_page, contact_page remain the same)
def landing_page(request):
    return render(request, 'landing.html')
def about_page(request):
    return render(request, 'about.html')
def contact_page(request):
    return render(request, 'contact.html')

# (signup_view, login_view, logout_view, dashboard_redirect_view remain the same as previous response)
def signup_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                logger.info(f"New user '{user.username}' created with role '{user.profile.role}'.")
                if user.profile.role == 'Worker':
                    logger.debug(f"New worker {user.username} signed up. Checking for pending tasks...")
                    user.profile.is_busy = False
                    user.profile.save(update_fields=['is_busy'])
                    try_assign_pending_task_to_worker(user)
                login(request, user)
                messages.success(request, "Registration successful! Welcome.")
                return redirect('dashboard_redirect')
            except Exception as e:
                 logger.error(f"Error during signup save or post-save actions: {e}", exc_info=True)
                 messages.error(request, "An unexpected error during registration. Please try again.")
                 form = CustomUserCreationForm()
        else:
            logger.warning(f"Signup form invalid. Errors: {form.errors.as_json()}")
            messages.error(request, "Registration failed. Please check the errors below.")
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                logger.info(f"User '{username}' logged in successfully.")
                if not hasattr(user, 'profile'):
                    logger.error(f"CRITICAL: User '{username}' logged in but has no UserProfile!")
                    messages.error(request, "Login successful, but profile incomplete. Contact support.")
                    logout(request)
                    return redirect('login')
                messages.info(request, f"Welcome back, {username}!")
                return redirect('dashboard_redirect')
            else:
                logger.warning(f"Failed login attempt for username: '{username}'")
                messages.error(request,"Invalid username or password.")
        else:
             messages.error(request,"Invalid login details.")
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})

def logout_view(request):
    if request.user.is_authenticated:
        logger.info(f"User '{request.user.username}' logged out.")
        logout(request)
        messages.info(request, "You have successfully logged out.")
    return redirect('landing_page')

@login_required
def dashboard_redirect_view(request):
    user = request.user
    logger.debug(f"Dashboard redirect for user '{user.username}'")
    if not hasattr(user, 'profile'):
        logger.error(f"User '{user.username}' redirecting but has no profile!")
        messages.error(request, "Profile missing or incomplete. Contact support.")
        logout(request)
        return redirect('login')
    role = user.profile.role
    if user.is_superuser or user.is_staff:
        logger.info(f"Redirecting admin user '{user.username}' to admin dashboard.")
        return redirect('admin_dashboard')
    elif role == 'Worker':
        logger.info(f"Redirecting worker user '{user.username}' to worker dashboard.")
        return redirect('worker_dashboard')
    elif role == 'Requestee':
        logger.info(f"Redirecting requestee user '{user.username}' to requestee dashboard.")
        return redirect('requestee_dashboard')
    else:
        logger.warning(f"User '{user.username}' has unknown role '{role}' in profile.")
        messages.warning(request, "Role not recognized. Contact support.")
        logout(request)
        return redirect('login')


# ============================
# === REQUESTEE VIEWS ======
# ============================

@requestee_required
def requestee_dashboard(request):
    """Displays the requestee's submitted requests."""
    my_requests = WasteRequest.objects.filter(requestee=request.user).select_related('assigned_worker').order_by('-updated_at')
    pending_approval = my_requests.filter(status='Pending Approval')
    other = my_requests.exclude(status='Pending Approval')
    context = {
        'pending_approval_requests': pending_approval,
        'other_requests': other,
    }
    return render(request, 'requestee/dashboard.html', context)

@requestee_required
def create_request_view(request):
    """Handles the creation of a new waste request by a requestee."""
    if request.method == 'POST':
        form = RequestCreationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                waste_request = form.save(commit=False)
                waste_request.requestee = request.user
                waste_request.status = 'Pending'
                waste_request.save()
                logger.info(f"Requestee '{request.user.username}' created Request ID: {waste_request.id} (Category: {waste_request.category})")
                messages.success(request, "Request submitted successfully! Assigning worker...")
                assigned = find_and_assign_worker(waste_request)
                if assigned:
                     messages.info(request, f"Worker '{waste_request.assigned_worker.username}' assigned.")
                else:
                     messages.info(request, "Request pending: Workers currently busy.")
                return redirect('requestee_dashboard')
            except Exception as e:
                 logger.error(f"Error saving request for user {request.user.username}: {e}", exc_info=True)
                 messages.error(request, "Error saving request. Please try again.")
        else:
             logger.warning(f"Request creation form invalid for user {request.user.username}. Errors: {form.errors.as_json()}")
             messages.error(request, "Request submission failed. Please check errors.")
    else:
        form = RequestCreationForm()
    return render(request, 'requestee/create_request.html', {'form': form})


@requestee_required
def approve_request_view(request, request_id):
    """
    Handles requestee approval/rejection and rating.
    Rating is saved REGARDLESS of approval status if form is valid.
    Average rating is updated REGARDLESS of approval status if form is valid.
    """
    waste_request = get_object_or_404(
        WasteRequest.objects.select_related('assigned_worker', 'assigned_worker__profile'),
        id=request_id,
        requestee=request.user,
        status='Pending Approval'
    )
    # <<< Get the worker who was assigned *before* potential clearing >>>
    original_worker = waste_request.assigned_worker

    if request.method == 'POST':
        form = ApprovalRatingForm(request.POST, instance=waste_request)
        if form.is_valid():
            logger.info(f"Processing approval/rating for Request ID: {request_id} by Requestee: {request.user.username}")
            approval_instance = form.save(commit=False) # Rating is now on the instance
            is_approved = form.cleaned_data.get('approve', False)

            # --- Perform state changes based on approval ---
            if is_approved:
                approval_instance.is_approved_by_student = True
                approval_instance.status = 'Completed'
                approval_instance.approved_at = timezone.now()
                logger.info(f"Request ID: {request_id} APPROVED by Requestee: {request.user.username}")
                messages.success(request, "Work approved and marked as Completed. Feedback submitted.")
            else:
                approval_instance.is_approved_by_student = False
                approval_instance.status = 'Pending' # Revert to Pending for re-assignment
                # Clear worker details ONLY AFTER saving rating and before checking for new worker
                approval_instance.assigned_worker = None
                approval_instance.assigned_at = None
                approval_instance.approved_at = None
                logger.info(f"Request ID: {request_id} REJECTED by Requestee: {request.user.username}. Status set to Pending.")
                if approval_instance.completion_image:
                    try:
                        approval_instance.completion_image.delete(save=False) # Delete file if rejected
                        logger.info(f"Deleted completion image for rejected Request ID: {request_id}")
                    except Exception as img_del_err:
                        logger.error(f"Error deleting completion_image for Request ID: {request_id}: {img_del_err}")
                approval_instance.completion_image = None # Clear field
                messages.warning(request, "Work not approved. Returned to Pending queue. Your rating has been recorded.")

            # --- Save the Request (Updates rating, status, approval flag, worker cleared if rejected) ---
            # The rating from the form is already on approval_instance because of form.save(commit=False)
            # and form = ApprovalRatingForm(request.POST, instance=waste_request)
            approval_instance.save()
            logger.debug(f"Saved Request ID: {request_id} with Status: {approval_instance.status}, Rating: {approval_instance.worker_rating}")

            # --- Update the ORIGINAL Worker's Average Rating ---
            # This should happen regardless of approval/rejection, as long as form was valid (rating was given)
            if original_worker:
                logger.debug(f"Attempting to update average rating for original worker: {original_worker.username}")
                try:
                    # Use the UserProfile model associated with the worker User
                    worker_profile = original_worker.profile
                    worker_profile.update_average_rating() # Call the method on the profile
                except UserProfile.DoesNotExist:
                    logger.error(f"UserProfile not found for worker {original_worker.username} during rating update!")
                    # Optionally create profile here if needed: WorkerProfile.objects.get_or_create(user=original_worker)
                except Exception as e:
                    logger.error(f"Could not update rating profile for worker {original_worker.username}. Error: {e}", exc_info=True)
            else:
                 logger.warning(f"Original worker not found for Request ID: {request_id} when updating rating.")

            # --- If Rejected, try immediate re-assignment for the PENDING task ---
            if not is_approved:
                logger.debug(f"Attempting immediate re-assignment for rejected Request ID: {request_id}")
                # Pass the instance which now has status='Pending' and no worker
                find_and_assign_worker(approval_instance)

            return redirect('requestee_dashboard')
        else:
            # Form invalid (rating was required but not provided)
            logger.warning(f"Approval/Rating form invalid for Request ID: {request_id}. Errors: {form.errors.as_json()}")
            messages.error(request, "Submission failed. Please select a rating.")
            # Fall through to re-render form with errors
    else:
        # GET request
        form = ApprovalRatingForm(instance=waste_request)

    context = { 'form': form, 'waste_request': waste_request }
    return render(request, 'requestee/approve_request.html', context)

# =======================
# === WORKER VIEWS ======
# =======================

@worker_required
def worker_dashboard(request):
    """Displays the worker's currently assigned task and average rating. Uses UserProfile."""
    worker = request.user
    # Check and update busy status first
    try:
        if hasattr(worker, 'profile'):
            worker.profile.update_busy_status()
        else:
            # Handle missing profile case - maybe create it?
             logger.error(f"UserProfile missing for worker {worker.username} on dashboard!")
             UserProfile.objects.get_or_create(user=worker, defaults={'role': 'Worker'}) # Attempt creation
    except Exception as e:
         logger.error(f"Error updating busy status for worker {worker.username} on dashboard: {e}")


    # Find the single task currently assigned (status='Assigned')
    current_task = WasteRequest.objects.filter(
        assigned_worker=worker,
        status='Assigned'
    ).select_related('requestee').first()

    # Get worker's average rating
    avg_rating = None
    rating_str = "Not Rated Yet"
    try:
        # Re-fetch profile after potential update_busy_status save
        worker_profile = UserProfile.objects.get(user=worker)
        avg_rating = worker_profile.average_rating
        if avg_rating is not None:
             rating_str = f"{avg_rating:.2f} / 5.00"
    except UserProfile.DoesNotExist:
        logger.error(f"UserProfile still missing for worker {worker.username} after get_or_create attempt!")
        rating_str = "Profile Error"
    except Exception as e:
        logger.error(f"Error fetching profile/rating for worker {worker.username} on dashboard: {e}", exc_info=True)
        rating_str = "Rating Error"

    # Get recently *approved* completed tasks for display history
    # <<< Corrected the filtering here >>>
    completed_tasks = WasteRequest.objects.filter(
        assigned_worker=worker,
        status='Completed' # Filter by the final 'Completed' status
    ).select_related('requestee').order_by('-approved_at')[:10] # Order by approval time


    context = {
        'current_task': current_task,
        'average_rating_str': rating_str,
        'completed_tasks': completed_tasks, # Pass completed tasks to template
    }
    return render(request, 'worker/dashboard.html', context)


@worker_required
def complete_task_view(request, request_id):
    """Handles the worker marking a task as complete and uploading proof. Uses UserProfile."""
    waste_request = get_object_or_404(
        WasteRequest,
        id=request_id,
        assigned_worker=request.user,
        status='Assigned'
    )
    logger.debug(f"Worker '{request.user.username}' viewing completion page for Request ID: {request_id}")

    if request.method == 'POST':
        form = WorkerCompletionForm(request.POST, request.FILES, instance=waste_request)
        if form.is_valid():
            try:
                completion_instance = form.save(commit=False)
                completion_instance.status = 'Pending Approval'
                completion_instance.save()

                logger.info(f"Worker '{request.user.username}' submitted Request ID: {request_id} for approval.")
                messages.success(request, "Task submitted for approval. Image uploaded.")

                # --- Mark worker as NOT busy ---
                try:
                    worker_profile = request.user.profile
                    worker_profile.is_busy = False
                    worker_profile.save(update_fields=['is_busy'])
                    logger.debug(f"Marked worker {request.user.username} as free.")
                    # --- Trigger check for pending tasks ---
                    try_assign_pending_task_to_worker(request.user)
                except UserProfile.DoesNotExist:
                     logger.error(f"UserProfile missing for worker {request.user.username} when trying to mark as free!")
                except Exception as e_busy:
                     logger.error(f"Error updating busy status or assigning next task for {request.user.username}: {e_busy}", exc_info=True)

                return redirect('worker_dashboard')

            except Exception as e:
                 logger.error(f"Error during task completion save for Request ID {request_id}: {e}", exc_info=True)
                 messages.error(request, "An error occurred while saving completion details.")

        else:
             logger.warning(f"Worker completion form invalid for Request ID: {request_id}. Errors: {form.errors.as_json()}")
             messages.error(request, "Upload failed. Please select a valid image file.")
    else:
        form = WorkerCompletionForm(instance=waste_request)

    context = { 'form': form, 'waste_request': waste_request }
    return render(request, 'worker/complete_task.html', context)


# ======================
# === ADMIN VIEWS ======
# ======================
# (admin_dashboard and admin_manual_assign_view remain the same as previous response)
@admin_required
def admin_dashboard(request):
    total_pending = WasteRequest.objects.filter(status='Pending').count()
    total_assigned = WasteRequest.objects.filter(status='Assigned').count()
    total_pending_approval = WasteRequest.objects.filter(status='Pending Approval').count()
    total_completed = WasteRequest.objects.filter(status='Completed').count()
    recent_pending = WasteRequest.objects.filter(status='Pending').select_related('requestee').order_by('-created_at')[:15]
    recent_assigned = WasteRequest.objects.filter(status='Assigned').select_related('requestee', 'assigned_worker').order_by('-assigned_at')[:15]
    recent_pending_approval = WasteRequest.objects.filter(status='Pending Approval').select_related('requestee', 'assigned_worker').order_by('-updated_at')[:15]
    recent_completed = WasteRequest.objects.filter(status='Completed').select_related('requestee', 'assigned_worker').order_by('-approved_at')[:15]
    context = {
        'total_pending': total_pending, 'total_assigned': total_assigned,
        'total_pending_approval': total_pending_approval, 'total_completed': total_completed,
        'recent_pending': recent_pending, 'recent_assigned': recent_assigned,
        'recent_pending_approval': recent_pending_approval, 'recent_completed': recent_completed,
    }
    return render(request, 'admin/dashboard.html', context)

@admin_required
def admin_manual_assign_view(request, request_id):
    waste_request = get_object_or_404(WasteRequest, id=request_id)
    logger.debug(f"Admin '{request.user.username}' viewing manual assignment page for Request ID: {request_id}")
    if waste_request.status != 'Pending':
        logger.warning(f"Admin '{request.user.username}' attempted manual assign on non-pending Request ID: {request_id} (Status: {waste_request.status})")
        messages.error(request, f"Manual assignment only allowed for 'Pending' requests. Status is '{waste_request.status}'.")
        return redirect('admin_dashboard')
    if request.method == 'POST':
        form = AdminManualAssignForm(request.POST, instance=waste_request)
        if form.is_valid():
            manual_assignment = form.save(commit=False)
            assigned_worker = manual_assignment.assigned_worker
            try:
                worker_profile = assigned_worker.profile
                if worker_profile.is_busy:
                    logger.warning(f"Admin '{request.user.username}' manual assign busy worker '{assigned_worker.username}' to Req ID: {request_id}")
                    messages.error(request, f"Worker '{assigned_worker.username}' is busy. Select a free worker.")
                    context = {'form': form, 'waste_request': waste_request}
                    return render(request, 'admin/assign_worker_override.html', context)
                manual_assignment.status = 'Assigned'
                manual_assignment.assigned_at = timezone.now()
                manual_assignment.save()
                worker_profile.is_busy = True
                worker_profile.save(update_fields=['is_busy'])
                logger.info(f"Admin '{request.user.username}' MANUALLY assigned Worker '{assigned_worker.username}' to Request ID: {request_id}")
                messages.success(request, f"Worker {assigned_worker.username} manually assigned!")
                return redirect('admin_dashboard')
            except UserProfile.DoesNotExist:
                 logger.error(f"UserProfile not found for manually assigned worker {assigned_worker.username}!")
                 messages.error(request, f"Cannot assign: Profile missing for worker {assigned_worker.username}.")
                 context = {'form': form, 'waste_request': waste_request}
                 return render(request, 'admin/assign_worker_override.html', context)
            except Exception as e:
                 logger.error(f"Error during manual assignment for Req ID {request_id}: {e}", exc_info=True)
                 messages.error(request, "Unexpected error during assignment.")
        else:
            logger.warning(f"Admin manual assignment form invalid for Req ID: {request_id}. Errors: {form.errors.as_json()}")
            messages.error(request, "Assignment failed. Please select a valid worker.")
    else:
        form = AdminManualAssignForm(instance=waste_request)
    workers_available = User.objects.filter(groups__name='Worker', is_active=True).exists()
    context = { 'form': form, 'waste_request': waste_request, 'workers_available': workers_available }
    return render(request, 'admin/assign_worker_override.html', context)

# ========================
# === ERROR VIEWS ========
# ========================
# (custom_404 and custom_500 remain the same)
def custom_404(request, exception):
    logger.warning(f"404 Not Found: {request.path} Exception: {exception}")
    return render(request, 'error.html', {'error_code': 404, 'error_message': 'Page Not Found'}, status=404)
def custom_500(request):
    logger.error(f"500 Internal Server Error at: {request.path}", exc_info=True)
    return render(request, 'error.html', {'error_code': 500, 'error_message': 'Internal Server Error'}, status=500)