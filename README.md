
# ✨ Cleanify V2 ✨ - Smart Campus Maintenance System

Cleanify V2 is a web application designed to streamline the reporting and resolution of maintenance issues (like sanitation, garbage collection, water leakage, and electricity problems) within a campus environment. It connects requestees (students/faculty) with available workers automatically, facilitating efficient task management and feedback.

---

## 🌟 Key Features

*   **Role-Based Access:** Dedicated dashboards and functionalities for three user roles:
    *   👤 **Requestee:** Can submit new service requests with details, category, and images. Track their requests and provide feedback.
    *   🛠️ **Worker:** Views assigned tasks specific to their category, uploads completion proof (images), and receives ratings.
    *   ⚙️ **Admin:** Oversees the system, views all requests, and can manually intervene in task assignments if necessary.
*   **Categorized Workers & Requests:** Workers are categorized (e.g., Sanitation, Electricity) and requests are tagged with a problem category for targeted assignment.
*   **🚀 Automatic Task Assignment:**
    *   New requests are automatically assigned to the first available (not busy) worker matching the request's category.
    *   If no worker is free, the request enters a 'Pending' queue.
    *   As soon as a relevant worker becomes free or a new worker of that category signs up, pending tasks are automatically assigned.
    *   Ensures one worker handles one task at a time (per the `is_busy` flag).
*   **📝 Detailed Request Creation:** Requestees can specify location, description, category of the issue, and upload an image as proof.
*   **📷 Image Uploads:**
    *   Requestees upload an image when creating a request.
    *   Workers upload a completion proof image when marking a task as done.
*   **✅ Approval & Rating System:**
    *   After a worker submits completion proof, the requestee reviews the work.
    *   Requestees can "Approve" or "Not Approve" the work.
    *   Requestees **must** provide a 1-5 star rating for the worker's service, regardless of approval.
    *   Worker's average rating is updated and displayed on their dashboard.
*   **🔄 Rejection & Re-assignment:**
    *   If a requestee does not approve the work, the task status reverts to 'Pending'.
    *   The submitted rating is still recorded for the original worker.
    *   The 'Pending' task re-enters the auto-assignment queue (and will not be immediately re-assigned to the same worker who just had it rejected, if other workers are available).
*   **🔑 Secure Signup & Login:**
    *   Users select their role (Requestee/Worker) during signup.
    *   Workers also select their service category during signup.
    *   Admin role is not available through public signup (created via `createsuperuser` or Django admin panel).
*   **🎨 Modern UI:**
    *   Attractive landing page with project information.
    *   Consistent header and footer across all pages.
    *   Styled using Tailwind CSS (via Play CDN for easy setup).
    *   Responsive design for various screen sizes.

---

## 🛠️ Technologies Used

*   **Backend:** Python, Django Framework
*   **Frontend:** HTML, Tailwind CSS (via Play CDN)
*   **Database:** SQLite (default, can be changed)
*   **Image Handling:** Pillow library

---

## 🚀 Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

*   Python (3.8+ recommended)
*   Pip (Python package installer)
*   (Optional but Recommended) Git for version control

### Installation & Setup

1.  **Clone the repository (or download the project files):**
    ```bash
    # If using Git:
    # git clone [URL_OF_REPOSITORY]
    # cd cleanify_v2_project
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # On Windows:
    # venv\Scripts\activate
    # On macOS/Linux:
    # source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(If you don't have `requirements.txt` yet, run `pip install Django Pillow` and then `pip freeze > requirements.txt`)*

4.  **Apply database migrations:**
    ```bash
    python manage.py makemigrations waste_management
    python manage.py migrate
    ```

5.  **Create a superuser (for Admin access):**
    ```bash
    python manage.py createsuperuser
    ```
    (Follow the prompts to create a username, email, and password)

6.  **Create Necessary Groups:**
    *   Run the development server: `python manage.py runserver`
    *   Go to the admin panel in your browser (e.g., `http://127.0.0.1:8000/secure-admin-panel/` - *check your actual admin URL in `cleanify_v2/urls.py`*).
    *   Login with your superuser credentials.
    *   Navigate to "Authentication and Authorization" -> "Groups".
    *   Add two groups with the exact names:
        *   `Requestee`
        *   `Worker`

7.  **Run the development server:**
    ```bash
    python manage.py runserver
    ```

8.  **Access the application:**
    Open your web browser and go to `http://127.0.0.1:8000/`

---

## 📋 Usage Workflow

1.  **Signup:**
    *   New users visit the "Sign Up" page.
    *   They choose their role: "Requestee" or "Worker".
    *   If "Worker" is chosen, they also select their service category.
    *   The system automatically creates their `UserProfile` and assigns them to the correct Django Group.
2.  **Login:** Users log in with their credentials. They are redirected to their role-specific dashboard.
3.  **Requestee Flow:**
    *   Views existing requests.
    *   Creates a new request (category, location, description, image).
    *   The system attempts to auto-assign a free worker of the matching category.
    *   When a worker marks a task as complete, the requestee gets it in their "Pending Approval" section.
    *   The requestee views the completion proof, provides a rating (mandatory), and chooses to "Approve" or "Not Approve".
4.  **Worker Flow:**
    *   Views their currently assigned task on their dashboard.
    *   Also sees their average rating.
    *   After completing the physical work, they upload a completion proof image and submit. The task status changes to "Pending Approval", and the worker becomes free.
    *   The system then checks if there are any pending tasks in their category to assign to them.
5.  **Admin Flow:**
    *   Views an overview of all requests (Pending, Assigned, Pending Approval, Completed).
    *   Can manually assign any 'Pending' request to a specific worker if needed (overrides auto-assignment for that instance).
    *   Manages users and groups through the Django Admin Panel.

---

## 🖼️ Screenshots 

## 🐛 Future Scope 

*   **Future Enhancements:**
    *   Real-time notifications for request status changes.
    *   Direct camera access for image uploads.
    *   Advanced image preview and change functionality before submission.
    *   Admin reports and worker performance metrics.
    *   Email notifications.

---

