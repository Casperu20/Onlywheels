from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import CartItem
from .serializers import AddItemSerializer, CartSerializer, MergeSerializer, UpdateItemSerializer


def cart_response(request) -> Response:
    cart = services.get_cart(request.user)
    items = list(services.cart_items(cart))
    data = {
        "items": items,
        "subtotal": services.subtotal(items),
        "item_count": sum(item.quantity for item in items),
    }
    return Response(CartSerializer(data, context={"request": request}).data)


class CartBaseView(APIView):
    permission_classes = (IsAuthenticated,)


@extend_schema(tags=["cart"])
class CartView(CartBaseView):
    @extend_schema(responses=CartSerializer)
    def get(self, request):
        return cart_response(request)

    @extend_schema(responses=CartSerializer)
    def delete(self, request):
        services.clear(services.get_cart(request.user))
        return cart_response(request)


@extend_schema(tags=["cart"])
class CartItemsView(CartBaseView):
    @extend_schema(request=AddItemSerializer, responses=CartSerializer)
    def post(self, request):
        serializer = AddItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.add_item(
            services.get_cart(request.user),
            serializer.validated_data["variant"],
            serializer.validated_data["quantity"],
        )
        return cart_response(request)


@extend_schema(tags=["cart"])
class CartItemDetailView(CartBaseView):
    def get_item(self, request, item_id) -> CartItem:
        return get_object_or_404(CartItem, pk=item_id, cart__user=request.user)

    @extend_schema(request=UpdateItemSerializer, responses=CartSerializer)
    def patch(self, request, item_id):
        serializer = UpdateItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.set_quantity(self.get_item(request, item_id), serializer.validated_data["quantity"])
        return cart_response(request)

    @extend_schema(responses=CartSerializer)
    def delete(self, request, item_id):
        self.get_item(request, item_id).delete()
        return cart_response(request)


@extend_schema(tags=["cart"])
class CartMergeView(CartBaseView):
    """Called once after login with the cart the guest built in the browser."""

    @extend_schema(request=MergeSerializer, responses=CartSerializer)
    def post(self, request):
        serializer = MergeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.merge(
            services.get_cart(request.user),
            [(line["variant_id"], line["quantity"]) for line in serializer.validated_data["items"]],
        )
        return cart_response(request)
