# waste_management/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm
from django.contrib.auth.models import User, Group
from django.db import transaction 

from .models import UserProfile, WasteRequest, ROLE_CHOICES, CATEGORY_CHOICES, RATING_CHOICES

import logging
logger = logging.getLogger(__name__)


class CustomUserCreationForm(BaseUserCreationForm):
    """ Extends default form to include Role and Worker Category selection. """
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        required=True,
        widget=forms.RadioSelect,
        help_text="Select your primary role in the system."
    )

    category = forms.ChoiceField(
        choices=[('', '--- Select Category (if Worker) ---')] + list(CATEGORY_CHOICES),
        required=False, 
        widget=forms.Select(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
        help_text="Required only if your role is 'Worker'."
    )

    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = BaseUserCreationForm.Meta.fields + ('role', 'category', 'first_name', 'last_name', 'email')

    def clean_email(self):
        # Make email required
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError("Email address is required.")
        if User.objects.filter(email=email).exists():
             raise forms.ValidationError("A user with this email address already exists.")
        return email

    def clean(self):
        """ Validate dependencies between fields (Role and Category). """
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        category = cleaned_data.get('category')

        if role == 'Worker' and not category:
            self.add_error('category', 'Category is required when selecting the Worker role.')
        elif role != 'Worker' and category:
            pass

        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        """
        Saves the User, creates/updates UserProfile, and assigns to appropriate Group.
        """
        user = super().save(commit=False)
      
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.email = self.cleaned_data.get('email')

        if commit:
            user.save() 

            role = self.cleaned_data.get('role')
            category = self.cleaned_data.get('category') if role == 'Worker' else None

            profile, created = UserProfile.objects.update_or_create(
                user=user,
                defaults={'role': role, 'category': category}
            )
            if created:
                logger.info(f"Created UserProfile for new user {user.username} with role {role}")
            else:
                 logger.warning(f"Updated existing UserProfile for user {user.username} during signup save.")


            try:
                user.groups.clear()
                group = Group.objects.get(name=role) 
                user.groups.add(group)
                logger.info(f"Added user {user.username} to group '{role}'")

            except Group.DoesNotExist:
                logger.error(f"CRITICAL: Group matching role '{role}' not found. Cannot assign group to user {user.username}.")
                pass
            except Exception as e:
                 logger.error(f"Error assigning group to user {user.username}: {e}", exc_info=True)


        return user


class RequestCreationForm(forms.ModelForm):
    """ Form for Requestees to create a new service request. """
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
       
        fields = ['category', 'location', 'description', 'request_image']
        widgets = {
            'location': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm', 'placeholder': 'E.g., Near Library, Room 303'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm', 'placeholder': 'Provide details about the issue (optional)'}),
        }



class WorkerCompletionForm(forms.ModelForm):
    """ Form for Workers to upload completion proof. """
    completion_image = forms.ImageField(
        required=True, 
        label="Upload Photo of Completed Work *",
        widget=forms.ClearableFileInput(attrs={'class': 'mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-violet-50 file:text-violet-700 hover:file:bg-violet-100'})
    )
    class Meta:
        model = WasteRequest
        fields = ['completion_image'] 


class ApprovalRatingForm(forms.ModelForm):
    """ Form for Requestees to approve/reject and rate completed work. """
    worker_rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'mr-2'}), 
        required=True,
        label="Rate the service provided: *"
    )
    approve = forms.BooleanField(
        required=False,
        label="Approve the completed work (Tick if satisfied)",
        widget=forms.CheckboxInput(attrs={'class':'h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded'})
    )

    class Meta:
        model = WasteRequest
        fields = ['worker_rating'] 


class AdminManualAssignForm(forms.ModelForm):
    """ Form for Admin to manually assign a worker to a PENDING request. """
 
    assigned_worker = forms.ModelChoiceField(
        queryset=User.objects.filter(groups__name='Worker', is_active=True).select_related('profile'),
        label="Assign Worker Manually",
        required=True, 
        empty_label="--- Select Available Worker ---",
        widget=forms.Select(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'})
    )

    class Meta:
        model = WasteRequest
        fields = ['assigned_worker']

    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_worker'].label_from_instance = self.worker_label

    def worker_label(self, user):
   
        category = user.profile.category if hasattr(user, 'profile') else 'N/A'
        busy_status = '(Busy)' if hasattr(user, 'profile') and user.profile.is_busy else '(Free)'
        return f"{user.username} [{category}] {busy_status}"