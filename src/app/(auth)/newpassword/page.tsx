'use client'
import { changePassword } from "@/lib/api/auth";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm, SubmitHandler } from "react-hook-form";

type FormData = {
  newPassword: string;
  confirmPassword: string;
};

export default function NewPassword() {
  const router = useRouter();
  const [serverError, setServerError] = useState("");

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormData>();

  const onSubmit: SubmitHandler<FormData> = async (data) => {
    try {
      setServerError("");
      await changePassword(data.newPassword);
      router.push("/dashboard");
    } catch (err: any) {
      setServerError(err.message);
    }
  };

  return (
    <div className="bg-[#EFF4FF] flex justify-center items-center h-screen">
      <div className="bg-white h-[30rem] w-[27.5rem] flex flex-col items-center rounded-lg shadow-xl">
        <h1 className="text-3xl text-[#00236F] font-bold mt-10">Nouveau mot de passe</h1>
        <p className="text-[#444651] mb-8">Veuillez entrer votre nouveau mot de passe ci-dessous</p>

        {serverError && <p className="text-red-500 text-sm">{serverError}</p>}

        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-2 mb-10 w-full px-6">
          <div className="flex flex-col gap-1 mb-2">
            <label htmlFor="newPassword">Nouveau mot de passe</label>
            <input
              className="bg-[#EFF4FF] py-3 rounded-md px-2 w-full text-[#757682]/60 font-light border border-[#E0E7FF]"
              id="newPassword"
              type="password"
              {...register("newPassword", {
                required: "Ce champ est obligatoire",
                minLength: {
                  value: 8,
                  message: "Le mot de passe doit contenir au moins 8 caractères",
                },
              })}
            />
            {errors.newPassword && (
              <p className="text-red-500 text-sm">{errors.newPassword.message}</p>
            )}
          </div>

          <div className="flex flex-col gap-1 mb-2">
            <label htmlFor="confirmPassword">Confirmer le mot de passe</label>
            <input
              className="bg-[#EFF4FF] py-3 rounded-md px-2 w-full text-[#757682]/60 font-light border border-[#E0E7FF]"
              id="confirmPassword"
              type="password"
              {...register("confirmPassword", {
                required: "Ce champ est obligatoire",
                validate: (value) =>
                  value === watch("newPassword") ||
                  "Les mots de passe ne correspondent pas",
              })}
            />
            {errors.confirmPassword && (
              <p className="text-red-500 text-sm">{errors.confirmPassword.message}</p>
            )}
          </div>

          <button
            type="submit"
            className="bg-linear-to-r from-[#00236f] to-[#1E3A8A] text-white w-full py-3 font-semibold rounded-lg flex justify-center items-center text-lg cursor-pointer transition-all active:scale-[0.99]"
            disabled={isSubmitting}
          >
            {isSubmitting ? "Enregistrement..." : "Enregistrer"}
          </button>
        </form>

        <Link href="/login" className="text-[#444651] font-light text-base">Retour à la connexion</Link>
      </div>
    </div>
  );
}