# waste_management/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm
from django.contrib.auth.models import User, Group
from django.db import transaction # For atomic operations during signup

from .models import UserProfile, WasteRequest, ROLE_CHOICES, CATEGORY_CHOICES, RATING_CHOICES

import logging
logger = logging.getLogger(__name__)

# --- Custom Signup Form ---

class CustomUserCreationForm(BaseUserCreationForm):
    """ Extends default form to include Role and Worker Category selection. """
    # Add role selection field
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        required=True,
        widget=forms.RadioSelect,
        help_text="Select your primary role in the system."
    )
    # Add worker category field (conditionally required/shown)
    category = forms.ChoiceField(
        choices=[('', '--- Select Category (if Worker) ---')] + list(CATEGORY_CHOICES), # Add placeholder
        required=False, # Initially not required, validated based on role
        widget=forms.Select(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
        help_text="Required only if your role is 'Worker'."
    )

    class Meta(BaseUserCreationForm.Meta):
        model = User
        # Fields from default form + our custom fields
        fields = BaseUserCreationForm.Meta.fields + ('role', 'category', 'first_name', 'last_name', 'email')

    def clean_email(self):
        # Make email required
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError("Email address is required.")
        # Add check for unique email if desired
        if User.objects.filter(email=email).exists():
             raise forms.ValidationError("A user with this email address already exists.")
        return email

    def clean(self):
        """ Validate dependencies between fields (Role and Category). """
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        category = cleaned_data.get('category')

        if role == 'Worker' and not category:
            # If role is Worker, category becomes required
            self.add_error('category', 'Category is required when selecting the Worker role.')
        elif role != 'Worker' and category:
            # If role is not Worker, category should be ignored (or raise error)
             # Let's just ignore it, the model's save method will clear it.
            pass

        return cleaned_data

    @transaction.atomic # Ensure user, profile, and group assignment happen together or not at all
    def save(self, commit=True):
        """
        Saves the User, creates/updates UserProfile, and assigns to appropriate Group.
        """
        # Save the User instance using the parent form's save method
        user = super().save(commit=False)
        # Set email and name fields if provided (add these fields to Meta.fields too)
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.email = self.cleaned_data.get('email')

        if commit:
            user.save() # Save the user first

            # Get role and category from cleaned data
            role = self.cleaned_data.get('role')
            category = self.cleaned_data.get('category') if role == 'Worker' else None

            # Create or update the UserProfile
            # Using update_or_create is safer if signup could be called multiple times somehow
            profile, created = UserProfile.objects.update_or_create(
                user=user,
                defaults={'role': role, 'category': category}
            )
            if created:
                logger.info(f"Created UserProfile for new user {user.username} with role {role}")
            else:
                 logger.warning(f"Updated existing UserProfile for user {user.username} during signup save.")


            # Assign user to the corresponding group
            try:
                # Remove from all groups first to handle role changes (though unlikely at signup)
                user.groups.clear()
                # Get the group matching the selected role
                group = Group.objects.get(name=role) # Group names MUST match ROLE_CHOICES
                user.groups.add(group)
                logger.info(f"Added user {user.username} to group '{role}'")

            except Group.DoesNotExist:
                logger.error(f"CRITICAL: Group matching role '{role}' not found. Cannot assign group to user {user.username}.")
                # Decide how to handle: raise error? Assign default? Log and continue?
                # For now, we log the error. The user exists but isn't in the right group.
                pass
            except Exception as e:
                 logger.error(f"Error assigning group to user {user.username}: {e}", exc_info=True)


        return user

# --- Request Creation Form ---

class RequestCreationForm(forms.ModelForm):
    """ Form for Requestees to create a new service request. """
    # Explicitly define category for better control if needed, otherwise Meta is fine
    category = forms.ChoiceField(
        choices=CATEGORY_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'})
    )
    request_image = forms.ImageField(
        required=True,
        label="Upload Image of Issue *",
        widget=forms.ClearableFileInput(attrs={'class': 'mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-violet-50 file:text-violet-700 hover:file:bg-violet-100'})
    )

    class Meta:
        model = WasteRequest
        # Fields the requestee needs to fill
        fields = ['category', 'location', 'description', 'request_image']
        widgets = {
            'location': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm', 'placeholder': 'E.g., Near Library, Room 303'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm', 'placeholder': 'Provide details about the issue (optional)'}),
        }

# --- Worker Completion Form ---

class WorkerCompletionForm(forms.ModelForm):
    """ Form for Workers to upload completion proof. """
    completion_image = forms.ImageField(
        required=True, # Image is mandatory
        label="Upload Photo of Completed Work *",
        widget=forms.ClearableFileInput(attrs={'class': 'mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-violet-50 file:text-violet-700 hover:file:bg-violet-100'})
    )
    class Meta:
        model = WasteRequest
        fields = ['completion_image'] # Only this field is submitted via this form

# --- Requestee Approval & Rating Form ---

class ApprovalRatingForm(forms.ModelForm):
    """ Form for Requestees to approve/reject and rate completed work. """
    worker_rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'mr-2'}), # Radio buttons for rating
        required=True, # Rating MUST be provided
        label="Rate the service provided: *"
    )
    # Non-model field for approval action
    approve = forms.BooleanField(
        required=False, # Not required; unchecking means rejection
        label="Approve the completed work (Tick if satisfied)",
        widget=forms.CheckboxInput(attrs={'class':'h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded'})
    )

    class Meta:
        model = WasteRequest
        fields = ['worker_rating'] # Rating maps directly to the model field

# --- Admin Manual Assignment Override Form ---

class AdminManualAssignForm(forms.ModelForm):
    """ Form for Admin to manually assign a worker to a PENDING request. """
    # Filter queryset to show only active workers
    assigned_worker = forms.ModelChoiceField(
        queryset=User.objects.filter(groups__name='Worker', is_active=True).select_related('profile'),
        label="Assign Worker Manually",
        required=True, # Must select a worker for manual assignment
        empty_label="--- Select Available Worker ---",
        widget=forms.Select(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'})
    )

    class Meta:
        model = WasteRequest
        fields = ['assigned_worker']

    # Optional: Customize how worker is displayed in dropdown
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_worker'].label_from_instance = self.worker_label

    def worker_label(self, user):
        # Display username and category in dropdown
        category = user.profile.category if hasattr(user, 'profile') else 'N/A'
        busy_status = '(Busy)' if hasattr(user, 'profile') and user.profile.is_busy else '(Free)'
        return f"{user.username} [{category}] {busy_status}"