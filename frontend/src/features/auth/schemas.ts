import { z } from "zod";

// Messages are i18n keys, translated by <FormField />.
const email = z.string().trim().min(1, "validation.required").email("validation.email");
const newPassword = z.string().min(8, "validation.passwordMin");

export const loginSchema = z.object({
  email,
  password: z.string().min(1, "validation.required"),
});
export type LoginValues = z.infer<typeof loginSchema>;

export const registerSchema = z
  .object({
    first_name: z.string().trim().max(150).optional(),
    last_name: z.string().trim().max(150).optional(),
    email,
    password: newPassword,
    confirmPassword: z.string(),
  })
  .refine((v) => v.password === v.confirmPassword, {
    message: "validation.passwordMatch",
    path: ["confirmPassword"],
  });
export type RegisterValues = z.infer<typeof registerSchema>;

export const forgotPasswordSchema = z.object({ email });
export type ForgotPasswordValues = z.infer<typeof forgotPasswordSchema>;

export const resetPasswordSchema = z
  .object({ password: newPassword, confirmPassword: z.string() })
  .refine((v) => v.password === v.confirmPassword, {
    message: "validation.passwordMatch",
    path: ["confirmPassword"],
  });
export type ResetPasswordValues = z.infer<typeof resetPasswordSchema>;

/** Only allow same-site relative paths as post-login redirect targets. */
export function safeNextPath(next: string | null, fallback = "/account"): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) {
    return fallback;
  }
  return next;
}
