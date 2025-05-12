from django.urls import path, include

urlpatterns = [
    path('catalog/', include('src.apps.catalog.api.urls')),
    path('cart/', include('src.apps.cart.api.urls')),
    path('orders/', include('src.apps.orders.api.urls')),
    path('users/', include('src.apps.accounts.api.urls')),
    path('wishlist/', include('src.apps.wishlist.api.urls')),
    path('reviews/', include('src.apps.reviews.api.urls')),
    path('loyalty/', include('src.apps.loyalty.api.urls')),
]