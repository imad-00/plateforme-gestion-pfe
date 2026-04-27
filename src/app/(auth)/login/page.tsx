'use client'
import Image from 'next/image'
import { SubmitHandler, useForm } from 'react-hook-form'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { loginUser } from '@/lib/api/auth'
import { useState } from 'react'
type FormData = {
  email: string;
  password: string;
};

export default function Home() {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>();

const router = useRouter();
const [serverError, setServerError] = useState('');

const onSubmit: SubmitHandler<FormData> = async (data) => {
  try {
    setServerError('');
    await loginUser(data.email, data.password);
    router.push('/dashboard'); // redirect after login
  } catch (err: any) {
    setServerError(err.message);
  }
};
  return (
    <div className="bg-[#EFF4FF] flex justify-center items-center h-screen ">
      <div className="bg-white h-120 w-110 flex flex-col items-center rounded-lg shadow-xl">
        <h1 className='text-3xl text-[#00236F] font-bold mt-10'>GradEx</h1>
        <p className='text-[#444651] mb-8'>L'excellence Academique</p>

        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-2 mb-10" >
          <div className='flex flex-col gap-1 mb-2'>
            <label htmlFor="email" className='text-sm text-[#444651] font-semibold'>Email</label>
            <input
              className='bg-[#EFF4FF] py-3 rounded-md px-2 w-95 text-[#757682]/60 font-light border border-[#E0E7FF]'
              {...register('email', {
                required: 'Email is required',
                pattern: {
                value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                message: 'Enter a valid email address',
              },
              })}
              type="email"
              placeholder="you@example.com"
            />
            {errors.email && <p className="text-red-500 text-sm">{errors.email.message}</p>}
          </div>

          <div className='flex flex-col gap-1 mb-3'>
            <div className='flex justify-between items-center text-sm font font-semibold'>
                          <label htmlFor="password" className='text-sm text-[#444651] font-semibold'>Password</label>
                          <Link href="/forgotpassword" className='text-[#4648D4] hover:underline'>Mot de passe oublié ?</Link>
            </div>

            <input
            className='bg-[#EFF4FF] py-3 rounded-md px-2 w-95 text-[#757682]/60 font-light border border-[#E0E7FF]'
            {...register('password', {
              required: 'Password is required',
              minLength: {
                value: 8,
                message: 'Password must be at least 8 characters',
              },
            })}
            type="password"
            placeholder="Enter your password"
          />
          {errors.password && <p className="text-red-500 text-sm">{errors.password.message}</p>}
          </div>
          

          <button className='bg-linear-to-r from-[#00236f] to-[#1E3A8A] text-white px-30 py-3 font-semibold rounded-lg flex justify-center items-center text-lg cursor-pointer group transition-all active:scale-99' type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Soumission...' : 'Se connecter'} <span className="group-hover:translate-x-1 transition-transform duration-200">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className='ml-1'>
              <path d="M5 12h14M12 5l7 7-7 7"/>
            </svg>
            </span>
          </button>
        </form>
        <p className='text-[#444651] font-light text-16px'>Accès réservé aux membres de l'institution.</p>
      </div>
    </div>
  );
}