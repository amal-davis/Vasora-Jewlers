from django.http import JsonResponse
from django.shortcuts import render
from django.shortcuts import get_object_or_404, redirect, render
from .models import *
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from urllib.parse import urlencode
import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt






def index(request):
    categories = Category.objects.all()
    latest_products = Product.objects.all().order_by('-created_at')[:4]
    trending_products = TrendingProduct.objects.all().order_by('-id')[:4]
    testimonials = Testimonial.objects.all()
    return render (request,'home.html',{'categories':categories,'latest_products':latest_products,'trending_products':trending_products,'testimonials':testimonials})


def about_us(request):
    categories = Category.objects.all()
    return render(request,'about_us.html',{'categories':categories})


def ex(request):
    return render (request,'example.html')

def products(request):
    sort_option = request.GET.get('sort', 'latest')

    if sort_option == 'low-to-high':
        all_products = Product.objects.all().order_by('discount_price', 'original_price')
    elif sort_option == 'high-to-low':
        all_products = Product.objects.all().order_by('-discount_price', '-original_price')
    elif sort_option == 'a-to-z':
        all_products = Product.objects.all().order_by('heading')
    elif sort_option == 'z-to-a':
        all_products = Product.objects.all().order_by('-heading')
    else:
        all_products = Product.objects.all().order_by('-created_at')

    paginator = Paginator(all_products, 20)  # 20 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    categories = Category.objects.all()

    return render(request, 'product.html', {'page_obj': page_obj, 'sort_option': sort_option,'categories':categories})
# Create your views here.


def product_details(request, slug):
    product = get_object_or_404(Product, slug=slug)
    categories = Category.objects.all()
    
    # Fetch related products from the same category, excluding the current product
    related_products = Product.objects.filter(category=product.category).exclude(id=product.id).order_by('-created_at')[:4]

    return render(request, 'product_details.html', {
        'product': product,
        'categories': categories,
        'related_products': related_products
    })


@login_required(login_url='signin')
def cart(request):
    cart_items = Cart.objects.filter(user=request.user)
    
    # Calculate total amount including delivery charges
    total_amount = sum(item.total_price for item in cart_items)
    total_delivery_charge = sum(item.product.delivery_charge for item in cart_items)
    categories = Category.objects.all()

    context = {
        'cart_items': cart_items,
        'total_amount': total_amount,
        'total_delivery_charge': total_delivery_charge,
        'categories':categories
    }
    return render(request, 'cart.html', context)



def remove_cart_item(request):
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        Cart.objects.filter(id=item_id, user=request.user).delete()

        # Recalculate the total amount including delivery charge
        cart_items = Cart.objects.filter(user=request.user)
        total_amount = sum(item.total_price for item in cart_items)

        return JsonResponse({
            'success': True,
            'total_amount': total_amount,
            'total_delivery_charge': sum(item.product.delivery_charge for item in cart_items),
            'item_count': cart_items.count(),
        })
    return JsonResponse({'success': False})



def update_cart_quantity(request):
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        new_quantity = int(request.POST.get('quantity'))

        cart_item = Cart.objects.get(id=item_id)
        cart_item.update_quantity(new_quantity)

        # Recalculate the total amount
        cart_items = Cart.objects.filter(user=request.user)
        total_amount = sum(item.total_price for item in cart_items)

        return JsonResponse({
            'item_total_price': cart_item.total_price,
            'total_amount': total_amount,
        })


def signup(request):
    categories = Category.objects.all()
    return render(request,'signup.html',{'categories':categories})



def login(request):
    categories = Category.objects.all()
    return render(request,'login.html',{'categories':categories})



def usercreate(request):
    if request.method == 'POST':
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        username = request.POST['username']
        password = request.POST['password']
        cpassword = request.POST['cpassword']
        email = request.POST['email']
        phone_no = request.POST['phone']

        if password == cpassword:
            # Check if the username is already taken
            if User.objects.filter(username=username).exists():
                messages.info(request, 'This username is already taken. Please choose a different one.')
                return redirect('signup_page')
            else:
                # Create the user and profile
                user = User.objects.create_user(
                    first_name=first_name,
                    last_name=last_name,
                    username=username,
                    password=password,
                    email=email
                )
                user.save()

                user_profile = UserProfile.objects.create(
                    user=user,
                    phone_number=phone_no
                )
                user_profile.save()
                print('Succeed....')
        else:
            messages.info(request, 'Passwords do not match!')
            print('Passwords do not match')
            return redirect('signup')

        return redirect('login')
    else:
        return render(request, 'signup.html')
    
@login_required(login_url='signin')
def admin_page(request):
    return render(request,'admin.html')


def signin(request):
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            auth_login(request, user)  # Use auth_login here

            if user.is_staff:
                return redirect('admin_page')  # Redirect admin users to the admin page
            else:
                return redirect('index')  # Redirect regular users to the index page
        else:
            messages.error(request, 'Invalid credentials. Please try again.')
            return render(request, 'login.html', context={'error': 'Invalid credentials'})

    return render(request, 'login.html')



def logout_view(request):
    logout(request)
    return redirect('index')



def contact_us(request):
    categories = Category.objects.all()
    return render(request,'contact_page.html',{'categories':categories})



def contact_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        message = request.POST.get('message')

        if name and email and phone and message:
            # Save the contact form data to the database
            Contact.objects.create(name=name, email=email, phone=phone, message=message)
            messages.success(request, 'Thank you for your message. We will get back to you shortly.')
            return redirect('contact_us')
        else:
            messages.error(request, 'Please fill in all fields.')


    return render(request, 'contact_page.html')



def message_list_view(request):
    messages = Contact.objects.all()
    categories = Category.objects.all()
    return render(request, 'message_list.html', {'messages': messages,'categories':categories})


def delete_message(request, pk):
    product_type = get_object_or_404(Contact, id=pk)
    
    product_type.delete()  # Delete the product type
    
    return redirect('message_list_view')  # Redirect to the list page


def add_category_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        image = request.FILES.get('image')

        if name:
            Category.objects.create(name=name, image=image)
            return redirect('add_category_view')  # Redirect to clear the form

    categories = Category.objects.all()
    return render(request, 'add_category.html', {'categories': categories})



def edit_category_view(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    if request.method == 'POST':
        name = request.POST.get('name')
        image = request.FILES.get('image')

        if name:
            category.name = name
            if image:
                category.image = image
            category.save()
            return redirect('add_category_view')

    return render(request, 'edit_category.html', {'category': category})




def delete_category(request, pk):
    product_type = get_object_or_404(Category, id=pk)
    
    product_type.delete()  # Delete the product type
    
    return redirect('add_category_view')  # Redirect to the list page




def add_product(request):
    if request.method == 'POST':
        category_id = request.POST.get('category')
        heading = request.POST.get('heading')
        description = request.POST.get('description')
        original_price = request.POST.get('original_price')
        discount_price = request.POST.get('discount_price')
        stock = request.POST.get('stock')
        delivery_charge = request.POST.get('delivery_charge', 0.00)

        # Create product instance
        product = Product.objects.create(
            category_id=category_id,
            heading=heading,
            description=description,
            original_price=original_price,
            discount_price=discount_price,
            stock=stock,
            delivery_charge=delivery_charge
        )

        # Handle multiple images
        images = request.FILES.getlist('images')
        for image in images:
            ProductImage.objects.create(product=product, image=image)

        return redirect('add_product')
    else:
        categories = Category.objects.all()
        products = Product.objects.all().order_by('-id')  # Ordered by latest first
        
        paginator = Paginator(products, 20)  # Show 20 products per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        return render(request, 'add_product.html', {
            'categories': categories,
            'page_obj': page_obj,
        })


def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        product.category_id = request.POST.get('category', product.category_id)
        product.heading = request.POST.get('heading', product.heading)
        product.description = request.POST.get('description', product.description)
        product.original_price = float(request.POST.get('original_price', product.original_price))
        product.discount_price = float(request.POST.get('discount_price', product.discount_price))
        product.stock = int(request.POST.get('stock', product.stock))
        product.delivery_charge = float(request.POST.get('delivery_charge', product.delivery_charge))
        product.save()

        # Handle new images if updated
        new_images = request.FILES.getlist('images')
        for image in new_images:
            ProductImage.objects.create(product=product, image=image)

        return redirect('add_product')

    context = {
        'product': product,
        'categories': Category.objects.all(),
    }

    return render(request, 'edit_product.html', context)



def p_delete_form(request,pk):
    edit=Product.objects.get(id=pk)
    edit.delete()
    return redirect('add_product')


@login_required(login_url='signin')
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))  # Get quantity from form

    # Check if the product is already in the cart
    cart_item, created = Cart.objects.get_or_create(user=request.user, product=product)

    if created:
        cart_item.quantity = quantity
    else:
        cart_item.quantity += quantity

    cart_item.save()

    messages.success(request, "Product added to your cart successfully!")
    return redirect('cart')  # Redirect to cart page or any other page



def category_products(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    sort_option = request.GET.get('sort', 'latest')

    if sort_option == 'low-to-high':
        products = Product.objects.filter(category=category).order_by('discount_price', 'original_price')
    elif sort_option == 'high-to-low':
        products = Product.objects.filter(category=category).order_by('-discount_price', '-original_price')
    elif sort_option == 'a-to-z':
        products = Product.objects.filter(category=category).order_by('heading')
    elif sort_option == 'z-to-a':
        products = Product.objects.filter(category=category).order_by('-heading')
    else:
        products = Product.objects.filter(category=category).order_by('-created_at')

    paginator = Paginator(products, 20)  # 20 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    categories = Category.objects.all()
    

    context = {
        'category': category,
        'page_obj': page_obj,
        'sort_option': sort_option,
        'categories':categories
    }
    return render(request, 'category_products.html', context)



def mark_trending(request):
    trending_products = TrendingProduct.objects.all()
    if request.method == 'POST':
        product_id = request.POST.get('product')
        product = get_object_or_404(Product, id=product_id)

        # Check if the product is already trending
        trending, created = TrendingProduct.objects.get_or_create(product=product)
        if created:
            # Product marked as trending successfully
            return redirect('mark_trending')
        else:
            # Product is already trending
            return redirect('mark_trending')

    products = Product.objects.all()
    return render(request, 'mark_trending.html', {'products': products,'trending_products':trending_products})


def trending_products(request):
    sort_option = request.GET.get('sort', 'latest')

    # Sorting logic
    if sort_option == 'low-to-high':
        trending_products = TrendingProduct.objects.all().order_by('product__discount_price', 'product__original_price')
    elif sort_option == 'high-to-low':
        trending_products = TrendingProduct.objects.all().order_by('-product__discount_price', '-product__original_price')
    elif sort_option == 'a-to-z':
        trending_products = TrendingProduct.objects.all().order_by('product__heading')
    elif sort_option == 'z-to-a':
        trending_products = TrendingProduct.objects.all().order_by('-product__heading')
    else:
        trending_products = TrendingProduct.objects.all().order_by('-product__created_at')

    # Pagination logic
    paginator = Paginator(trending_products, 20)  # 20 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'trending_products.html', {
        'page_obj': page_obj,
        'sort_option': sort_option
    })


def delete_trending_product(request, product_id):
    trending_product = get_object_or_404(TrendingProduct, id=product_id)
    trending_product.delete()
    messages.success(request, "Product removed from trending successfully!")
    return redirect('mark_trending')  # Redirect to the manage trending products page


@login_required(login_url='signin')
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    Wishlist.objects.get_or_create(user=request.user, product=product)
    return redirect('wishlist') # Redirect to the wishlist page or any other page

@login_required(login_url='signin')
def remove_from_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    wishlist_item = get_object_or_404(Wishlist, user=request.user, product=product)
    wishlist_item.delete()
    messages.success(request, "Product removed from your wishlist.")
    
    return redirect('wishlist')  # Redirect to the wishlist page or any other page

@login_required(login_url='signin')
def wishlist(request):
    wishlist_items = Wishlist.objects.filter(user=request.user)
    return render(request, 'wishlist.html', {'wishlist_items': wishlist_items})



@login_required(login_url='signin')
def checkout(request):
    cart_items = Cart.objects.filter(user=request.user)

    # Calculate the total amount and delivery charges
    total_amount = sum(item.total_price for item in cart_items)
    total_delivery_charge = sum(item.product.delivery_charge for item in cart_items)

    # Add Razorpay details to the context
    context = {
        'cart_items': cart_items,
        'total_amount': total_amount,
        'total_delivery_charge': total_delivery_charge,
        'razorpay_key': settings.RAZORPAY_API_KEY,  # Pass the Razorpay API key to the frontend
    }

    return render(request, 'checkout.html', context)

@login_required(login_url='signin')
def process_order(request):
    if request.method == 'POST':
        # Log the incoming POST data for debugging
        print("POST data received:", request.POST)

        # Get the subtotal and delivery charge from the form data
        subtotal = float(request.POST.get('subtotal', 0))
        delivery_charge = float(request.POST.get('delivery_charge', 0))

        # Determine the total amount to be charged. If subtotal already includes the delivery charge, then:
        total_amount = subtotal  # Use this if subtotal includes delivery charge

        # If the delivery charge should be added separately, uncomment the following:
        # total_amount = subtotal + delivery_charge

        # Create a Razorpay order
        client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))
        razorpay_order = client.order.create({
            'amount': int(total_amount * 100),  # Razorpay expects the amount in paisa
            'currency': 'INR',
            'payment_capture': '1'
        })

        # Pass the Razorpay order ID and other details to the frontend
        return JsonResponse({
            'order_id': razorpay_order['id'],
            'amount': total_amount,
            'currency': 'INR',
            'key': settings.RAZORPAY_API_KEY,
            'name': 'Your Company Name',
            'description': 'Order Payment',
            'prefill': {
                'name': request.POST['first_name'] + ' ' + request.POST['last_name'],
                'email': request.POST['email'],
                'contact': request.POST['phone'],
            },
            'callback_url': request.build_absolute_uri('/payment-callback/'),
            'customer_data': request.POST,  # Pass the customer data for use in the callback
        })

    else:
        return redirect('cart')







def order_success(requset):
    categories = Category.objects.all()
    return render(requset,'order_success.html',{'categories':categories})


def order_failure(request):
    return render(request,'order_failure.html')



@csrf_exempt
def payment_callback(request):
    if request.method == 'POST':
        payment_id = request.POST.get('razorpay_payment_id')
        order_id = request.POST.get('razorpay_order_id')
        signature = request.POST.get('razorpay_signature')

        client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))
        params_dict = {
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }

        # Log the parameters for debugging
        print("Payment Callback Parameters:", params_dict)

        try:
            # Verify the payment signature
            client.utility.verify_payment_signature(params_dict)

            # If verification is successful, create the order and save customer details
            customer_data = request.POST

            customer = Customer.objects.create(
                first_name=customer_data['first_name'],
                last_name=customer_data['last_name'],
                country=customer_data['country'],
                address=customer_data['address'],
                city=customer_data['city'],
                phone=customer_data['phone'],
                email=customer_data['email']
            )

            subtotal = float(customer_data['subtotal'])
            delivery_charge = float(customer_data['delivery_charge'])

            # Create the order
            order = Order.objects.create(
                customer=customer,
                user=request.user,
                subtotal=subtotal,
                delivery_charge=delivery_charge,
                status='Confirmed',
                payment_id=order_id  # Store the Razorpay order ID
            )

            # Move items from cart to order
            cart_items = Cart.objects.filter(user=request.user)
            for item in cart_items:
                item_total_price = item.quantity * (item.product.discount_price if item.product.discount_price else item.product.original_price)
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item_total_price
                )
                # Decrease the stock of the ordered products
                item.product.decrease_stock(item.quantity)

            # Clear the cart after moving items to the order
            cart_items.delete()

            return JsonResponse({"success": True})

        except razorpay.errors.SignatureVerificationError as e:
            print("Signature verification failed:", str(e))

            return JsonResponse({"success": False, "error": "Signature verification failed"})

    return JsonResponse({"success": False})











@login_required(login_url='signin')
def user_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    # Set up pagination
    paginator = Paginator(orders, 12)  # 12 orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'user_orders.html', {'page_obj': page_obj})




@login_required(login_url='signin')
def manage_orders(request):
    orders = Order.objects.all().order_by('-created_at')
    paginator = Paginator(orders, 12)  # Show 12 orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'manage_orders.html', {'page_obj': page_obj})


@login_required(login_url='signin')
def update_order_status(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        order.status = request.POST['status']
        order.save()
        return redirect('manage_orders')



def search_results(request):
    query = request.GET.get('q')
    products = Product.objects.filter(heading__icontains=query) if query else Product.objects.none()

    context = {
        'query': query,
        'products': products
    }
    return render(request, 'search_results.html', context)




def add_testimonial_view(request):
    if request.method == 'POST':
        print(request.POST)  # Check all POST data
        client_name = request.POST.get('client_name')
        location = request.POST.get('location')
        image = request.FILES.get('image')
        testimonial_text = request.POST.get('testimonial_text')

        if testimonial_text:
            Testimonial.objects.create(client_name=client_name, image=image, location=location, testimonial_text=testimonial_text)
            return redirect('add_testimonial_view')  # Redirect to clear the form

    testimonials = Testimonial.objects.all()
    return render(request, 'add_testimonal.html', {'testimonials': testimonials})


def edit_testimonial_view(request, testimonial_id):
    testimonial = get_object_or_404(Testimonial, id=testimonial_id)
    
    if request.method == 'POST':
        # Process form submission
        testimonial.client_name = request.POST.get('client_name')
        testimonial.location = request.POST.get('location')
        testimonial.testimonial_text = request.POST.get('testimonial_text')
        
        if 'image' in request.FILES:
            testimonial.image = request.FILES['image']
        
        testimonial.save()
        return redirect('add_testimonial_view')  # Redirect to the testimonials list page

    return render(request, 'edit_testimonial.html', {'testimonial': testimonial})


def delete_testimonial(request, testimonial_id):
    # Retrieve the specific testimonial by ID
    testimonial = get_object_or_404(Testimonial, id=testimonial_id)
    
    if request.method == 'POST':
        # Delete the testimonial from the database
        testimonial.delete()
        return redirect('add_testimonial_view')  # Redirect to the testimonials list page

    # If it's a GET request, show a confirmation page
    return render(request, 'add_testimonal.html', {'testimonial': testimonial})




def terms_and_condition(request):
    categories = Category.objects.all()
    return render(request,'terms_and_condition.html',{'categories':categories})