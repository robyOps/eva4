from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from apps.inventory.models import Product
from apps.sales.models import CartItem


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
    return render(request, 'login.html')


@login_required
def dashboard(request):
    return render(request, 'dashboard.html')


def product_list(request):
    products = Product.objects.all()
    return render(request, 'shop/products.html', {'products': products})


def product_detail(request, pk):
    product = Product.objects.get(pk=pk)
    return render(request, 'shop/product_detail.html', {'product': product})


@login_required
def cart_view(request):
    items = CartItem.objects.filter(user=request.user)
    return render(request, 'shop/cart.html', {'items': items})


@login_required
def checkout_view(request):
    return render(request, 'shop/checkout.html')
