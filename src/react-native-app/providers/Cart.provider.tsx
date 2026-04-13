// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0
/**
 * Copied with modification from src/frontend/providers/Cart.provider.tsx
 */
import React, { createContext, useCallback, useContext, useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import ApiGateway from "@/gateways/Api.gateway";
import { CartItem, OrderResult, PlaceOrderRequest } from "@/protos/demo";
import { IProductCart } from "@/types/Cart";

interface IContext {
  cart: IProductCart;
  addItem(item: CartItem): void;
  updateItem(productId: string, quantity: number): void;
  removeItem(productId: string): void;
  emptyCart(): void;
  placeOrder(order: PlaceOrderRequest): Promise<OrderResult>;
  isLoading: boolean;
}

export const Context = createContext<IContext>({
  cart: { userId: "", items: [] },
  addItem: () => {},
  updateItem: () => {},
  removeItem: () => {},
  emptyCart: () => {},
  placeOrder: () => Promise.resolve({} as OrderResult),
  isLoading: false,
});

interface IProps {
  children: React.ReactNode;
}

export const useCart = () => useContext(Context);

const CartProvider = ({ children }: IProps) => {
  // TODO simplify react native demo for now by hard-coding the selected currency
  const selectedCurrency = "USD";
  const queryClient = useQueryClient();
  const mutationOptions = useMemo(
    () => ({
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["cart"] });
      },
    }),
    [queryClient],
  );

  const { data: cart = { userId: "", items: [] }, isLoading } = useQuery({
    queryKey: ["cart", selectedCurrency],
    queryFn: () => ApiGateway.getCart(selectedCurrency),
  });
  
  const addCartMutation = useMutation({
    mutationFn: ApiGateway.addCartItem, 
    ...mutationOptions
  });
  const updateCartMutation = useMutation({
    mutationFn: ({ productId, quantity }: { productId: string; quantity: number }) =>
      ApiGateway.updateCartItem(productId, quantity, selectedCurrency),
    ...mutationOptions
  });
  const removeCartMutation = useMutation({
    mutationFn: (productId: string) => ApiGateway.removeCartItem(productId, selectedCurrency),
    ...mutationOptions
  });
  const emptyCartMutation = useMutation({
    mutationFn: ApiGateway.emptyCart, 
    ...mutationOptions
  });
  const placeOrderMutation = useMutation({
    mutationFn: ApiGateway.placeOrder,
    ...mutationOptions
  });

  const addItem = useCallback(
    (item: CartItem) =>
      addCartMutation.mutateAsync({ ...item, currencyCode: selectedCurrency }),
    [addCartMutation, selectedCurrency],
  );

  const updateItem = useCallback(
    (productId: string, quantity: number) =>
      updateCartMutation.mutateAsync({ productId, quantity }),
    [updateCartMutation],
  );

  const removeItem = useCallback(
    (productId: string) =>
      removeCartMutation.mutateAsync(productId),
    [removeCartMutation],
  );

  const emptyCart = useCallback(
    () => emptyCartMutation.mutateAsync(),
    [emptyCartMutation],
  );

  const placeOrder = useCallback(
    (order: PlaceOrderRequest) =>
      placeOrderMutation.mutateAsync({
        ...order,
        currencyCode: selectedCurrency,
      }),
    [placeOrderMutation, selectedCurrency],
  );

  const value = useMemo(
    () => ({ 
      cart, 
      addItem, 
      updateItem,
      removeItem,
      emptyCart, 
      placeOrder,
      isLoading 
    }),
    [cart, addItem, updateItem, removeItem, emptyCart, placeOrder, isLoading],
  );

  return <Context.Provider value={value}>{children}</Context.Provider>;
};

export default CartProvider;
