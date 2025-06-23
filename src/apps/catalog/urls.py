from django.urls import include, path

# from rest_framework.routers import DefaultRouter

# from .views import ProductViewSet, CategoryViewSet, BrandViewSet

# Catalog router
# catalog_router = DefaultRouter()
# catalog_router.register(r'products', ProductViewSet, basename='products')
# catalog_router.register(r'categories', CategoryViewSet, basename='categories')
# catalog_router.register(r'brands', BrandViewSet, basename='brands')

# Product catalog module URLs
# Base path: /api/v1/catalog/
urlpatterns = [
    # Product management
    path(
        "products/",
        include(
            [
                # path('', ProductViewSet.as_view({'get': 'list', 'post': 'create'}), name='products'),
                # path('<int:product_id>/', ProductViewSet.as_view({
                #     'get': 'retrieve',
                #     'patch': 'partial_update',
                #     'delete': 'destroy'
                # }), name='product_detail'),
                # path('<int:product_id>/variants/', ProductViewSet.as_view({
                #     'get': 'variants'
                # }), name='product_variants'),
                # path('<int:product_id>/images/', ProductViewSet.as_view({
                #     'get': 'images',
                #     'post': 'add_image'
                # }), name='product_images'),
            ]
        ),
    ),
    # Category management
    path(
        "categories/",
        include(
            [
                # path('', CategoryViewSet.as_view({'get': 'list', 'post': 'create'}), name='categories'),
                # path('<int:category_id>/', CategoryViewSet.as_view({
                #     'get': 'retrieve',
                #     'patch': 'partial_update',
                #     'delete': 'destroy'
                # }), name='category_detail'),
                # path('<int:category_id>/products/', CategoryViewSet.as_view({
                #     'get': 'products'
                # }), name='category_products'),
                # path('tree/', CategoryViewSet.as_view({'get': 'tree'}), name='category_tree'),
            ]
        ),
    ),
    # Brand management
    path(
        "brands/",
        include(
            [
                # path('', BrandViewSet.as_view({'get': 'list', 'post': 'create'}), name='brands'),
                # path('<int:brand_id>/', BrandViewSet.as_view({
                #     'get': 'retrieve',
                #     'patch': 'partial_update',
                #     'delete': 'destroy'
                # }), name='brand_detail'),
                # path('<int:brand_id>/products/', BrandViewSet.as_view({
                #     'get': 'products'
                # }), name='brand_products'),
            ]
        ),
    ),
    # Search and filtering
    path(
        "search/",
        include(
            [
                # path('', ProductViewSet.as_view({'get': 'search'}), name='search'),
                # path('suggestions/', ProductViewSet.as_view({'get': 'search_suggestions'}), name='search_suggestions'),
                # path('filters/', ProductViewSet.as_view({'get': 'available_filters'}), name='available_filters'),
            ]
        ),
    ),
    # Placeholder endpoint for module existence
    path("", lambda request: None, name="catalog_root"),
]

app_name = "catalog"
