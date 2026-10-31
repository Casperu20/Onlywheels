import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Car, MapPin, Pencil, Plus, Star, Trash2 } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { toast } from "sonner";
import { z } from "zod";

import { applyFieldErrors, getErrorMessage } from "@/api/errors";
import { FormField } from "@/components/FormField";
import { PageLoader } from "@/components/PageLoader";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { useMe, useUpdateMe, type User } from "@/features/auth";
import { ProductGrid } from "@/features/catalog";
import { checkoutApi, useAddresses, type Address } from "@/features/checkout";
import { useFavorites } from "@/features/favorites";
import {
  VehicleSelector,
  useAddMyVehicle,
  useMyVehicles,
  useRemoveMyVehicle,
  useVehicleStore,
  vehicleLabel,
} from "@/features/vehicle";

export function GaragePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data: vehicles, isPending } = useMyVehicles();
  const addVehicle = useAddMyVehicle();
  const removeVehicle = useRemoveMyVehicle();
  const { active, setActive } = useVehicleStore();

  return (
    <section className="container-page flex flex-col gap-8 py-10">
      <div>
        <p className="text-[10px] font-bold tracking-[2px] text-primary uppercase">{t("account.eyebrow")}</p>
        <h1 className="mt-2 text-4xl font-extrabold md:text-5xl">{t("nav.garage")}</h1>
        <p className="mt-2 text-muted-foreground">{t("garage.subtitle")}</p>
      </div>

      <div className="rounded-2xl border border-border bg-card p-6">
        <h2 className="mb-4 text-sm font-semibold">{t("garage.add")}</h2>
        <VehicleSelector
          submitLabel={t("garage.save")}
          disabled={addVehicle.isPending}
          onSelect={(generation) =>
            addVehicle.mutate(
              { generation_id: generation.id, is_default: !vehicles?.length },
              {
                onSuccess: () => toast.success(t("garage.saved")),
                onError: (error) => toast.error(getErrorMessage(error, t("auth.genericError"))),
              },
            )
          }
        />
      </div>

      {isPending ? (
        <PageLoader />
      ) : vehicles?.length ? (
        <ul className="grid gap-3 md:grid-cols-2">
          {vehicles.map((vehicle) => {
            const label = vehicleLabel(vehicle.generation, t("vehicle.present"));
            const isActive = active?.id === vehicle.generation.id;
            return (
              <li key={vehicle.id} className="flex flex-col gap-4 rounded-2xl border border-border p-5">
                <div className="flex items-start gap-3">
                  <Car className="mt-0.5 size-5 text-primary" aria-hidden />
                  <div>
                    <p className="font-semibold">{vehicle.nickname || label}</p>
                    {vehicle.nickname && <p className="text-xs text-muted-foreground">{label}</p>}
                    {!vehicle.generation.has_fitment && (
                      <p className="mt-1 text-xs text-destructive">{t("garage.noFitment")}</p>
                    )}
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant={isActive ? "secondary" : "default"}
                    onClick={() => {
                      setActive({ id: vehicle.generation.id, label });
                      navigate(`/catalog?type=wheel&vehicle=${vehicle.generation.id}`);
                    }}
                  >
                    {t("garage.shopFor")}
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={removeVehicle.isPending}
                    onClick={() => removeVehicle.mutate(vehicle.id)}
                  >
                    <Trash2 aria-hidden /> {t("garage.remove")}
                  </Button>
                </div>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="text-muted-foreground">{t("garage.empty")}</p>
      )}
    </section>
  );
}

export function FavoritesPage() {
  const { t } = useTranslation();
  const { data, isLoading } = useFavorites();

  return (
    <section className="container-page flex flex-col gap-8 py-10">
      <div>
        <p className="text-[10px] font-bold tracking-[2px] text-primary uppercase">{t("account.eyebrow")}</p>
        <h1 className="mt-2 text-4xl font-extrabold md:text-5xl">{t("favorites.title")}</h1>
      </div>
      <ProductGrid
        products={data?.results}
        isLoading={isLoading}
        skeletonCount={4}
        emptyTitle={t("favorites.emptyTitle")}
        emptyText={t("favorites.emptyText")}
      />
    </section>
  );
}

const optionalPhone = z.union([z.literal(""), z.string().trim().regex(/^\+?[0-9 ]{9,16}$/, "validation.phone")]);

const profileSchema = z.object({
  first_name: z.string().trim().max(150),
  last_name: z.string().trim().max(150),
  phone: optionalPhone,
  preferred_language: z.enum(["ro", "en"]),
});

const required = z.string().trim().min(1, "validation.required");

const addressSchema = z.object({
  full_name: required.max(150),
  phone: z.string().trim().regex(/^\+?[0-9 ]{9,16}$/, "validation.phone"),
  line1: required.max(255),
  line2: z.string().trim().max(255),
  city: required.max(100),
  county: required.max(100),
  postal_code: z.string().trim().regex(/^[0-9]{6}$/, "validation.postalCode"),
  is_default: z.boolean(),
});

type AddressValues = z.infer<typeof addressSchema>;

export function ProfilePage() {
  const { t } = useTranslation();
  const { data: user } = useMe();
  if (!user) return null;

  return (
    <section className="container-page flex flex-col gap-8 py-10">
      <div>
        <p className="text-[10px] font-bold tracking-[2px] text-primary uppercase">{t("account.eyebrow")}</p>
        <h1 className="mt-2 text-4xl font-extrabold md:text-5xl">{t("profile.title")}</h1>
        <p className="mt-2 text-muted-foreground">{t("profile.subtitle")}</p>
      </div>
      <div className="grid items-start gap-6 lg:grid-cols-[1fr_1.4fr]">
        <ProfileForm user={user} />
        <AddressBook />
      </div>
    </section>
  );
}

function ProfileForm({ user }: { user: User }) {
  const { t, i18n } = useTranslation();
  const updateMe = useUpdateMe();
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting, isDirty, dirtyFields },
    reset,
  } = useForm({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      first_name: user.first_name,
      last_name: user.last_name,
      phone: user.phone,
      preferred_language: user.preferred_language,
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    const languageChanged = Boolean(dirtyFields.preferred_language);
    try {
      const saved = await updateMe.mutateAsync(values);
      reset({
        first_name: saved.first_name,
        last_name: saved.last_name,
        phone: saved.phone,
        preferred_language: saved.preferred_language,
      });
      if (languageChanged) void i18n.changeLanguage(saved.preferred_language);
      toast.success(t("profile.saved"));
    } catch (error) {
      if (!applyFieldErrors(error, setError)) toast.error(getErrorMessage(error, t("auth.genericError")));
    }
  });

  return (
    <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4 rounded-2xl border border-white/[0.08] bg-card p-6">
      <h2 className="text-lg font-bold">{t("profile.details")}</h2>
      <FormField label={t("auth.email")} value={user.email} disabled readOnly />
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField
          label={t("auth.firstName")}
          autoComplete="given-name"
          error={errors.first_name?.message}
          {...register("first_name")}
        />
        <FormField
          label={t("auth.lastName")}
          autoComplete="family-name"
          error={errors.last_name?.message}
          {...register("last_name")}
        />
      </div>
      <FormField
        label={t("checkout.phone")}
        type="tel"
        autoComplete="tel"
        error={errors.phone?.message}
        {...register("phone")}
      />
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="preferred-language">{t("profile.language")}</Label>
        <NativeSelect id="preferred-language" {...register("preferred_language")}>
          <option value="ro">Română</option>
          <option value="en">English</option>
        </NativeSelect>
      </div>
      <Button type="submit" disabled={isSubmitting || !isDirty} className="self-start">
        {t("profile.save")}
      </Button>
    </form>
  );
}

function AddressBook() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: addresses, isPending } = useAddresses();
  const [editing, setEditing] = useState<Address | "new" | null>(null);
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["addresses"] });
  const remove = useMutation({ mutationFn: checkoutApi.deleteAddress, onSuccess: refresh });
  const makeDefault = useMutation({
    mutationFn: (id: string) => checkoutApi.updateAddress({ id, is_default: true }),
    onSuccess: refresh,
  });

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-white/[0.08] bg-card p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-bold">{t("profile.addresses")}</h2>
        {editing === null && (
          <Button size="sm" variant="secondary" onClick={() => setEditing("new")}>
            <Plus aria-hidden /> {t("profile.addAddress")}
          </Button>
        )}
      </div>

      {editing !== null && (
        <AddressForm
          address={editing === "new" ? undefined : editing}
          isFirst={!addresses?.length}
          onDone={() => setEditing(null)}
        />
      )}

      {isPending ? (
        <PageLoader />
      ) : addresses?.length ? (
        <ul className="grid gap-3">
          {addresses.map((address) => (
            <li
              key={address.id}
              className="flex flex-col gap-3 rounded-xl border border-white/[0.08] p-4 sm:flex-row sm:items-start sm:justify-between"
            >
              <div className="flex gap-3">
                <MapPin className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden />
                <div className="text-sm">
                  <p className="font-semibold">
                    {address.full_name}
                    {address.is_default && (
                      <span className="ml-2 rounded-full bg-success/15 px-2 py-0.5 text-[10px] font-bold text-success uppercase">
                        {t("profile.default")}
                      </span>
                    )}
                  </p>
                  <p className="text-muted-foreground">
                    {[address.line1, address.line2].filter(Boolean).join(", ")}
                  </p>
                  <p className="text-muted-foreground">
                    {address.postal_code} {address.city}, {address.county}
                  </p>
                  <p className="text-muted-foreground">{address.phone}</p>
                </div>
              </div>
              <div className="flex flex-wrap gap-1">
                {!address.is_default && (
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={makeDefault.isPending}
                    onClick={() => makeDefault.mutate(address.id)}
                  >
                    <Star aria-hidden /> {t("profile.makeDefault")}
                  </Button>
                )}
                <Button size="sm" variant="ghost" onClick={() => setEditing(address)}>
                  <Pencil aria-hidden /> {t("profile.edit")}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={remove.isPending}
                  onClick={() => remove.mutate(address.id, { onSuccess: () => toast.success(t("profile.deleted")) })}
                >
                  <Trash2 aria-hidden /> {t("garage.remove")}
                </Button>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        editing === null && <p className="text-sm text-muted-foreground">{t("profile.noAddresses")}</p>
      )}
    </div>
  );
}

function AddressForm({ address, isFirst, onDone }: { address?: Address; isFirst: boolean; onDone: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<AddressValues>({
    resolver: zodResolver(addressSchema),
    defaultValues: {
      full_name: address?.full_name ?? "",
      phone: address?.phone ?? "",
      line1: address?.line1 ?? "",
      line2: address?.line2 ?? "",
      city: address?.city ?? "",
      county: address?.county ?? "",
      postal_code: address?.postal_code ?? "",
      is_default: address?.is_default ?? isFirst,
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    try {
      if (address) await checkoutApi.updateAddress({ id: address.id, ...values });
      else await checkoutApi.saveAddress(values);
      await queryClient.invalidateQueries({ queryKey: ["addresses"] });
      toast.success(t("profile.addressSaved"));
      onDone();
    } catch (error) {
      if (!applyFieldErrors(error, setError)) toast.error(getErrorMessage(error, t("auth.genericError")));
    }
  });

  return (
    <form onSubmit={onSubmit} noValidate className="grid gap-4 rounded-xl border border-primary/30 bg-primary/[0.04] p-4 sm:grid-cols-2">
      <FormField label={t("checkout.fullName")} autoComplete="name" error={errors.full_name?.message} {...register("full_name")} />
      <FormField label={t("checkout.phone")} type="tel" autoComplete="tel" error={errors.phone?.message} {...register("phone")} />
      <FormField
        label={t("checkout.line1")}
        autoComplete="address-line1"
        containerClassName="sm:col-span-2"
        error={errors.line1?.message}
        {...register("line1")}
      />
      <FormField
        label={t("checkout.line2")}
        autoComplete="address-line2"
        containerClassName="sm:col-span-2"
        error={errors.line2?.message}
        {...register("line2")}
      />
      <FormField label={t("checkout.city")} autoComplete="address-level2" error={errors.city?.message} {...register("city")} />
      <FormField label={t("checkout.county")} autoComplete="address-level1" error={errors.county?.message} {...register("county")} />
      <FormField
        label={t("checkout.postalCode")}
        inputMode="numeric"
        autoComplete="postal-code"
        error={errors.postal_code?.message}
        {...register("postal_code")}
      />
      <label className="flex items-center gap-2 self-end pb-3 text-sm">
        <input type="checkbox" className="size-4 accent-primary" {...register("is_default")} />
        {t("profile.makeDefault")}
      </label>
      <div className="flex gap-2 sm:col-span-2">
        <Button type="submit" disabled={isSubmitting}>
          {t("profile.saveAddress")}
        </Button>
        <Button type="button" variant="ghost" onClick={onDone}>
          {t("common.cancel")}
        </Button>
      </div>
    </form>
  );
}
