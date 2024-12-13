from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import UserUpdateForm, ProfileUpdateForm
from django.views.decorators.cache import cache_page


@login_required
@cache_page(60 * 15)
def profile(request):
    return render(request, 'users/profile.html')


@login_required
@cache_page(60 * 15)
def edit_profile(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            return redirect('users:profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user)
    context = {
        'user_form': user_form,
        'profile_form': profile_form
    }
    return render(request, 'users/edit_profile.html', context)
