import { z } from "zod";

// Messages are i18n keys (see <FormField />). Rules mirror apps/orders/serializers.py.
const required = z.string().trim().min(1, "validation.required");

export const checkoutSchema = z.object({
  delivery_method: z.enum(["courier", "garage_fitting"]),
  email: required.email("validation.email"),
  full_name: required.max(150),
  phone: z.string().trim().regex(/^\+?[0-9 ]{9,16}$/, "validation.phone"),
  line1: required.max(255),
  line2: z.string().trim().max(255).optional(),
  city: required.max(100),
  county: required.max(100),
  postal_code: z.string().trim().regex(/^[0-9]{6}$/, "validation.postalCode"),
  notes: z.string().max(1000).optional(),
  save_address: z.boolean(),
  accept_terms: z.boolean().refine((value) => value, "validation.acceptTerms"),
});

export type CheckoutValues = z.infer<typeof checkoutSchema>;
