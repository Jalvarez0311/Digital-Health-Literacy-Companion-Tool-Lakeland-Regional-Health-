document.addEventListener("DOMContentLoaded", () => {

  // Welcome Page Buttons
  const nurseBtn = document.getElementById("nurseBtn");
  const patientBtn = document.getElementById("patientBtn");

  if (nurseBtn && patientBtn) {
    nurseBtn.addEventListener("click", () => {
      localStorage.setItem("userType", "nurse");
      window.location.href = "/auth/";  // Django URL
    });

    patientBtn.addEventListener("click", () => {
      localStorage.setItem("userType", "patient");
      window.location.href = "/auth/";  // Django URL
    });
  }

  // Authentication Page
  const loginForm = document.getElementById("loginForm");
  const signupForm = document.getElementById("signupForm");
  const backBtn = document.getElementById("backBtn");

  if (loginForm && signupForm && backBtn) {
    const usernameInput = document.getElementById("username");
    const passwordInput = document.getElementById("password");
    const newUsername = document.getElementById("newUsername");
    const newPassword = document.getElementById("newPassword");
    const loginMessage = document.getElementById("loginMessage");
    const signupMessage = document.getElementById("signupMessage");
    const showSignupLink = document.getElementById("showSignup");

    const userType = localStorage.getItem("userType") || "user";
    if (userType === "nurse") {
      usernameInput.placeholder = "Nurse ID";
      newUsername.placeholder = "Nurse ID";
    } else if (userType === "patient") {
      usernameInput.placeholder = "Patient Username";
      newUsername.placeholder = "Patient Username";
    }

    // Back Button goes to welcome page
    backBtn.addEventListener("click", () => {
      window.location.href = "/";  // Django welcome URL
    });

    // Show Signup Form
    showSignupLink.addEventListener("click", (e) => {
      e.preventDefault();
      loginForm.style.display = "none";
      signupForm.style.display = "block";
      showSignupLink.parentElement.style.display = "none";
      loginMessage.innerText = "";
    });

    /* Simulated Login
    loginForm.addEventListener("submit", (e) => {
      e.preventDefault();
      if (usernameInput.value === "user" && passwordInput.value === "Web_dev!") {
        window.location.href = "/dashboard/";  // Django dashboard URL
      } else {
        loginMessage.innerText = "Invalid username or password.";
        loginMessage.style.color = "red";
      }
    });
    */

    // Simulated Signup
    signupForm.addEventListener("submit", (e) => {
      e.preventDefault();
      signupMessage.innerText = "Account created! Please log in.";
      signupMessage.style.color = "green";
      setTimeout(() => {
        signupForm.style.display = "none";
        loginForm.style.display = "block";
        signupMessage.innerText = "";
        showSignupLink.parentElement.style.display = "block";
      }, 1000);
    });
  }
  
  // Dashboard Logic
  const logoutBtn = document.getElementById("logoutBtn");

  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => {
        // Clear any localStorage info if needed
        localStorage.removeItem("userType");

        // Redirect to the welcome page
        window.location.href = "/";
    });
  }

});
