from django.urls import include, path

# from rest_framework.routers import DefaultRouter

# from .views import OrderViewSet, CartViewSet, CheckoutViewSet

# Orders module URLs
# Base path: /api/v1/orders/
urlpatterns = [
    # Shopping cart management
    path(
        "cart/",
        include(
            [
                # path('', CartViewSet.as_view({
                #     'get': 'retrieve',
                #     'post': 'add_item',
                #     'delete': 'clear'
                # }), name='cart'),
                # path('items/<int:item_id>/', CartViewSet.as_view({
                #     'patch': 'update_item',
                #     'delete': 'remove_item'
                # }), name='cart_item'),
                # path('summary/', CartViewSet.as_view({'get': 'summary'}), name='cart_summary'),
                # path('validate/', CartViewSet.as_view({'post': 'validate'}), name='cart_validate'),
            ]
        ),
    ),
    # Order management
    path(
        "",
        include(
            [
                # path('', OrderViewSet.as_view({
                #     'get': 'list',
                #     'post': 'create'
                # }), name='orders'),
                # path('<int:order_id>/', OrderViewSet.as_view({
                #     'get': 'retrieve',
                #     'patch': 'partial_update'
                # }), name='order_detail'),
                # path('<int:order_id>/cancel/', OrderViewSet.as_view({
                #     'post': 'cancel'
                # }), name='cancel_order'),
                # path('<int:order_id>/track/', OrderViewSet.as_view({
                #     'get': 'tracking'
                # }), name='track_order'),
                # path('<int:order_id>/invoice/', OrderViewSet.as_view({
                #     'get': 'invoice'
                # }), name='order_invoice'),
            ]
        ),
    ),
    # Checkout process
    path(
        "checkout/",
        include(
            [
                # path('', CheckoutViewSet.as_view({'post': 'initiate'}), name='initiate_checkout'),
                # path('shipping/', CheckoutViewSet.as_view({
                #     'get': 'shipping_options',
                #     'post': 'set_shipping'
                # }), name='checkout_shipping'),
                # path('payment/', CheckoutViewSet.as_view({
                #     'get': 'payment_methods',
                #     'post': 'process_payment'
                # }), name='checkout_payment'),
                # path('confirm/', CheckoutViewSet.as_view({'post': 'confirm'}), name='checkout_confirm'),
            ]
        ),
    ),
    # Payment processing
    path(
        "payments/",
        include(
            [
                # path('methods/', CheckoutViewSet.as_view({'get': 'payment_methods'}), name='payment_methods'),
                # path('process/', CheckoutViewSet.as_view({'post': 'process_payment'}), name='process_payment'),
                # path('webhooks/stripe/', CheckoutViewSet.as_view({'post': 'stripe_webhook'}), name='stripe_webhook'),
                # path('webhooks/paypal/', CheckoutViewSet.as_view({'post': 'paypal_webhook'}), name='paypal_webhook'),
            ]
        ),
    ),
    # Returns and refunds
    path(
        "returns/",
        include(
            [
                # path('', OrderViewSet.as_view({
                #     'get': 'returns',
                #     'post': 'request_return'
                # }), name='returns'),
                # path('<int:return_id>/', OrderViewSet.as_view({
                #     'get': 'return_detail',
                #     'patch': 'update_return'
                # }), name='return_detail'),
            ]
        ),
    ),
]

app_name = "orders"
