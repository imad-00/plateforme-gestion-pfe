'use client'
import { SubmitHandler, useForm } from 'react-hook-form'
import Image from 'next/image';
import forgotImg from '../../../public/Background.png'
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { sendResetOTP } from '@/lib/api/auth';
type FormData = {
  email: string;
};

export default function ForgotPassword() {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>();
  const router = useRouter();
    const onSubmit: SubmitHandler<FormData> = async (data) => {
    try {
        await sendResetOTP(data.email);
        router.push(`/verify-otp?email=${data.email}`);
    } catch (err: any) {
    console.error(err.message);
  }
}

  return (
    <div className="bg-[#EFF4FF] flex justify-center items-center h-screen">
      <div className="bg-white w-110 h-110 flex flex-col items-center rounded-lg shadow-xl px-10 py-8">
        <Image src={forgotImg} alt='none' className='mb-2'></Image>
        <h1 className="text-3xl text-[#0B1C30] font-bold">Mot de passe oublié</h1>
        <p className="text-[#444651] text-sm text-center mt-2 mb-4">
          Saisissez votre adresse email pour recevoir un code de réinitialisation.
        </p>
text-[#0B1C30]
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-2 w-full">
          <div className="flex flex-col gap-1 mb-2">
            <label htmlFor="email" className="text-sm text-[#444651] font-semibold">Email</label>
            <input
              className="bg-[#EFF4FF] py-3 rounded-md px-2 w-full text-[#757682]/60 font-light border border-[#E0E7FF]"
              {...register('email', {
                required: 'Email is required',
                pattern: {
                  value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                  message: 'Enter a valid email address',
                },
              })}
              id="email"
              type="email"
              placeholder="votre.nom@institution.edu"
            />
            {errors.email && <p className="text-red-500 text-sm">{errors.email.message}</p>}
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="bg-linear-to-r from-[#00236f] to-[#1E3A8A] text-white w-full py-3 font-semibold rounded-lg flex items-center justify-center gap-1 text-lg group hover:shadow-lg active:scale-95 transition-all cursor-pointer mb-6"
          >
            {isSubmitting ? 'Envoi...' : 'Envoyer le code'} <span className="group-hover:translate-x-1 transition-transform duration-200">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className='ml-1'>
              <path d="M5 12h14M12 5l7 7-7 7"/>
            </svg>
            </span>
          </button>
        </form>
        <Link href='/login' className='font-light hover:underline text-[#444651]'>Retour a la connexion</Link>
      </div>
    </div>
  );
}