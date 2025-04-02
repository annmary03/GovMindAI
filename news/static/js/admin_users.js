// Wrap everything in a self-executing function to create a global scope
(function() {
    // Global variables
    window.users = [];
    window.selectedUserId = null;

    // Initialize everything when the DOM is ready
    document.addEventListener("DOMContentLoaded", function () {
        document.getElementById("saveUserBtn").addEventListener("click", window.saveUser);
        

        // Fetch users on initial page load
        window.fetchUsers();

        // Reset form when modal is opened for a new user
        const userModal = document.getElementById('userModal');
        userModal.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            if (!button.hasAttribute('data-user-id')) {
                // New user
                window.resetForm();
                document.getElementById('userModalLabel').textContent = 'Add New User';
                document.getElementById('passwordHelpText').style.display = 'none';
            }
        });
    });

    // Fetch users from the API
    window.fetchUsers = function() {
        fetch('/api/admin/users/')
        .then(response => response.json())
        .then(data => {
            console.log('Fetched users:', data); // Added for debugging
            if (data.success) {
                window.users = data.users; // Assuming the API returns an object with a 'users' array
                window.renderUsersTable();
            } else {
                console.error('Failed to fetch users:', data.error);
                alert('Failed to load users');
            }
        })
        .catch(error => {
            console.error('Error fetching users:', error);
            alert('An error occurred while fetching users');
        });
    };

    // Render the users table
    window.renderUsersTable = function() {
        const tableBody = document.getElementById('users-table-body');
        tableBody.innerHTML = '';
        
        window.users.forEach(user => {
            const row = document.createElement('tr');
            
            row.innerHTML = `
                <td>${user.username}</td>
                <td>${user.email}</td>
                <td>${user.first_name || ''} ${user.last_name || ''}</td>
                <td>
                    <span class="badge ${user.is_staff ? 'bg-success' : 'bg-secondary'}">
                        ${user.is_staff ? 'Yes' : 'No'}
                    </span>
                </td>
                <td>
                    <span class="badge ${user.is_active ? 'bg-success' : 'bg-danger'}">
                        ${user.is_active ? 'Active' : 'Inactive'}
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm btn-primary me-1" onclick="editUser(${user.id})">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path>
                        </svg>
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="showDeleteModal(${user.id})">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="3 6 5 6 21 6"></polyline>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                        </svg>
                    </button>
                </td>
            `;
            
            tableBody.appendChild(row);
        });
    };

    window.saveUser = function(event) {
        console.log("Save button clicked!");
        event.preventDefault();
    
        const userId = document.getElementById("userId").value;
        const username = document.getElementById("username").value;
        const email = document.getElementById("email").value;
        const password = document.getElementById("password").value;
        const department = document.getElementById("department").value;
        const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value; // Get from Django's csrf_token
    
        if (!username || !email) {
            alert("Username and Email are required fields.");
            return;
        }
        if (!userId && !password) {
            alert("Password is required for new users.");
            return;
        }
    
        const data = {
            username,
            email,
            password,
            department,
            is_staff: false
        };
    
        const url = userId ? `/admin/update-user/${userId}/` : "/admin/add-user/";
        const method = userId ? "PUT" : "POST";
    
        fetch(url, {
            method: method,
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(result => {
            console.log('Save user response:', result);
            if (result.success) {
                alert("User saved successfully!");
                bootstrap.Modal.getInstance(document.getElementById('userModal')).hide();
                window.fetchUsers(); // Refresh the users list
            } else {
                alert("Error: " + (result.message || "Failed to save user"));
            }
        })
        .catch(error => {
            console.error("Error:", error);
            alert("An error occurred while saving the user.");
        });
    };

    window.editUser = function(userId) {
        const user = window.users.find(u => u.id === userId);
        if (!user) return;
        
        // Set form values
        document.getElementById('userId').value = user.id;
        document.getElementById('username').value = user.username;
        document.getElementById('email').value = user.email;
        document.getElementById('password').value = ''; // Clear password field
        document.getElementById('department').value = user.department || ''; // Use department
        
        // Update modal title and show password help text
        document.getElementById('userModalLabel').textContent = 'Edit User';
        document.getElementById('passwordHelpText').style.display = 'block';
        
        // Show the modal
        const userModal = new bootstrap.Modal(document.getElementById('userModal'));
        userModal.show();
    };

    window.showDeleteModal = function(userId) {
        window.selectedUserId = userId;
        const deleteModal = new bootstrap.Modal(document.getElementById('deleteModal'));
        deleteModal.show();
    };

    window.deleteUser = function() {
        if (!window.selectedUserId) return;
        
        fetch('/api/admin/users/', {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': window.getCsrfToken()
            },
            body: JSON.stringify({ id: window.selectedUserId })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Close the modal and refresh the users list
                const deleteModal = bootstrap.Modal.getInstance(document.getElementById('deleteModal'));
                deleteModal.hide();
                window.fetchUsers();
            } else {
                alert('Error: ' + (data.error || 'Failed to delete user'));
            }
        })
        .catch(error => {
            console.error('Error deleting user:', error);
            alert('Failed to delete user. Please try again.');
        });
    };

    window.resetForm = function() {
        document.getElementById('userForm').reset();
        document.getElementById('userId').value = '';
    };

    window.getCsrfToken = function() {
        const name = 'csrftoken';
        let cookieValue = null;
        
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        
        return cookieValue;
    };
})();