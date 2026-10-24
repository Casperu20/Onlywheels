import { useId, type ComponentProps } from "react";
import { useTranslation } from "react-i18next";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

interface FormFieldProps extends ComponentProps<typeof Input> {
  label: string;
  /** i18n key ("validation.*") from zod, or an already-translated message from the API */
  error?: string;
  containerClassName?: string;
}

export function FormField({ label, error, id, containerClassName, ...inputProps }: FormFieldProps) {
  const { t } = useTranslation();
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const errorId = `${inputId}-error`;

  return (
    <div className={cn("flex flex-col gap-1.5", containerClassName)}>
      <Label htmlFor={inputId}>{label}</Label>
      <Input
        id={inputId}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        {...inputProps}
      />
      {error && (
        <p id={errorId} className="text-xs text-destructive">
          {error.startsWith("validation.") ? t(error) : error}
        </p>
      )}
    </div>
  );
}
