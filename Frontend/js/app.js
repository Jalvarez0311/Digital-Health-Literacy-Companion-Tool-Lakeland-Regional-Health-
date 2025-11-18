// Actual Frontend Logic

// Check if frontend JS is loaded
console.log("Frontend loaded!!");

// Listen for specific event
document.addEventListener("DOMContentLoaded", () => {
  /*
  
    Welcome Page Logic: 
  
  */
  const nurseBtn = document.getElementById("nurseBtn");
  const patientBtn = document.getElementById("patientBtn");

  if (nurseBtn && patientBtn) {
    nurseBtn.addEventListener("click", () => {
      localStorage.setItem("userType", "nurse");
      window.location.href = "auth.html";
    });

    patientBtn.addEventListener("click", () => {
      localStorage.setItem("userType", "patient");
      window.location.href = "auth.html";
    });
  }

  /*
  
    Authentication Page Logic: 
  
  */
  const loginForm = document.getElementById("loginForm");
  const signupForm = document.getElementById("signupForm");
  const backBtn = document.getElementById("backBtn");

  if (loginForm && signupForm) {
    const usernameInput = document.getElementById("username");
    const passwordInput = document.getElementById("password");
    const passwordStrength = document.getElementById("passwordStrength");

    const newUsername = document.getElementById("newUsername");
    const newPassword = document.getElementById("newPassword");
    const signupPasswordStrength = document.getElementById("signupPasswordStrength");
    const signupMessage = document.getElementById("signupMessage");

    const showSignupLink = document.getElementById("showSignup");
    const loginMessage = document.getElementById("loginMessage");

    const userType = localStorage.getItem("userType") || "user";

    // Update placeholders for role
    if (userType === "nurse") {
      usernameInput.placeholder = "Nurse ID";
      newUsername.placeholder = "Nurse ID";
    } else if (userType === "patient") {
      usernameInput.placeholder = "Patient Username";
      newUsername.placeholder = "Patient Username";
    }

    // Back Button
    backBtn.addEventListener("click", () => {
      window.location.href = "index.html";
    });

    // Feedback during signup, password strength check
    function getPasswordFeedback(pw) {
      const feedback = [];
      if (pw.length < 8) feedback.push("at least 8 characters");
      if (!/[A-Z]/.test(pw)) feedback.push("at least one UPPERCASE letter");
      if (!/[\W]/.test(pw)) feedback.push("at least one special character");
      return feedback;
    }

    // Feedback as user types password during signup
    newPassword.addEventListener("input", () => {
      const feedback = getPasswordFeedback(newPassword.value);
      if (feedback.length === 0) {
        signupPasswordStrength.innerText = "Password meets all requirements.";
      } else {
        signupPasswordStrength.innerText = "Password must have " + feedback.join(", ")+ ".";
      }
    });

    // Toggle? For signup and login ???
    showSignupLink.addEventListener("click", (e) => {
      e.preventDefault();
      loginForm.style.display = "none";
      signupForm.style.display = "block";
      loginMessage.innerText = "";
      
      // Hide the signup link on the sign up page
      showSignupLink.parentElement.style.display = "none";

    });

  
    // Login submission, simulated
    loginForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const user = usernameInput.value.trim();
      const pass = passwordInput.value;

      if (!user || !pass) {
        loginMessage.innerText = "Please enter login info.";
        loginMessage.style.color = "red";
        return;
      }

      // Credentials, also simulated
      if (user === "user" && pass === "Web_dev!") {
        loginMessage.innerText = ""; // no message if login successful
        setTimeout(() => { window.location.href = "discharge.html"; }, 500);
      } else {
        loginMessage.innerText = "Invalid username or password.";
        loginMessage.style.color = "red";
      }
    });

    // Signup submission, simulated
    signupForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const user = newUsername.value.trim();
      const pass = newPassword.value;
      const feedback = getPasswordFeedback(pass);

      if (!user || !pass) {
        signupMessage.innerText = "Please enter signup info.";
        signupMessage.style.color = "red";
        return;
      }

      if (feedback.length > 0) {
        signupMessage.innerText = "Password must have: " + feedback.join(", ");
        signupMessage.style.color = "red";
        return;
      }

      signupMessage.innerText = "Account created! Please log in.";
      signupMessage.style.color = "green";

      setTimeout(() => {
        signupForm.style.display = "none";
        loginForm.style.display = "block";
        signupMessage.innerText = "";

        // Show signup link again
        showSignupLink.parentElement.style.display = "block";

      }, 1000);
    });
  }
});