from django.shortcuts import render, redirect

def auth_view(request):
    message = ""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        # Test login logic
        if username == "test" and password == "test":
            # Successful login: redirect to dashboard
            return redirect("dashboard")
        else:
            message = "Incorrect username or password."

    return render(request, "companion/auth.html", {"message": message})


def dashboard(request):
    return render(request, "companion/dashboard.html")


def welcome(request):
    return render(request, "companion/welcome.html")
