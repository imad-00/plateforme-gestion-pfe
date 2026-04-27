'use client'
import { useState, useRef, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'

export default function VerifyEmail() {
  const [otp, setOtp] = useState(['', '', '', '', '', ''])
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [resendTimer, setResendTimer] = useState(59)
  const [canResend, setCanResend] = useState(false)
  const inputs = useRef<(HTMLInputElement | null)[]>([])
  const router = useRouter()
  const params = useSearchParams()
  const email = params.get('email') || 'votre email'

  // ✅ Countdown that actually ticks
  useEffect(() => {
    if (resendTimer <= 0) { setCanResend(true); return; }
    const timer = setTimeout(() => setResendTimer(t => t - 1), 1000)
    return () => clearTimeout(timer)
  }, [resendTimer])

  const handleResend = async () => {
    if (!canResend) return
    try {
      // await resendOTP(email)
      setResendTimer(59)
      setCanResend(false)
      setError('')
    } catch {
      setError("Échec de l'envoi. Veuillez réessayer.")
    }
  }

  const handleChange = (index: number, value: string) => {
    if (!/^\d*$/.test(value)) return
    const newOtp = [...otp]
    newOtp[index] = value.slice(-1)
    setOtp(newOtp)
    if (value && index < 5) inputs.current[index + 1]?.focus()
  }

  const handleKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      inputs.current[index - 1]?.focus()
    }
  }

  const handleSubmit = async () => {
    const code = otp.join('')
    if (code.length < 6) { setError('Veuillez entrer les 6 chiffres.'); return; }
    setIsSubmitting(true)
    setError('')
    try {
      console.log('OTP submitted:', code)
      // await verifyOTP(email, code)
      router.push('/newpassword')
    } catch {
      setError('Code invalide. Veuillez réessayer.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="bg-[#EFF4FF] flex justify-center items-center h-screen">
      {/* ✅ w-110 → w-[27.5rem] */}
      <div className="bg-white w-[27.5rem] flex flex-col items-center rounded-lg shadow-xl px-10 py-10">

        <div className="bg-[#EFF4FF] p-4 rounded-full mb-4">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#4648D4" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <rect x="2" y="4" width="20" height="16" rx="2"/>
            <path d="M2 7l10 7 10-7"/>
          </svg>
        </div>

        <h1 className="text-2xl text-[#0B1C30] font-bold text-center">Vérifiez votre e-mail</h1>
        <p className="text-[#444651] text-sm text-center mt-2 mb-1">
          Nous avons envoyé un code de vérification à 6 chiffres à
        </p>
        <p className="text-[#4648D4] font-medium text-sm mb-6">{email}</p>

        <div className="flex gap-3 mb-2">
          {otp.map((digit, i) => (
            <input
              key={i}
              ref={el => { inputs.current[i] = el }}
              type="text"
              inputMode="numeric"
              maxLength={1}
              value={digit}
              onChange={e => handleChange(i, e.target.value)}
              onKeyDown={e => handleKeyDown(i, e)}
              className={`w-12 h-12 text-center text-xl font-semibold rounded-lg border-2 outline-none transition-all mb-4
                ${error ? 'border-red-400 bg-red-50 text-red-500' : 'border-[#E0E7FF] bg-[#EFF4FF] text-[#0B1C30] focus:border-[#4648D4]'}`}
            />
          ))}
        </div>

        {error && (
          <p className="text-red-500 text-sm mb-3 flex items-center gap-1">
            <span>⚠</span> {error}
          </p>
        )}

        <button
          onClick={handleSubmit}
          disabled={isSubmitting}
          className="bg-gradient-to-r from-[#00236f] to-[#1E3A8A] text-white w-full py-3 font-semibold rounded-lg flex items-center justify-center gap-2 hover:shadow-lg active:scale-95 transition-all cursor-pointer mt-4 mb-6 disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {isSubmitting ? 'Vérification...' : 'Vérifier'}
        </button>

        <p className="text-[#444651] text-sm">Vous n'avez pas reçu le code ?</p>

        {/* ✅ Real resend button that activates when timer expires */}
        {canResend ? (
          <button
            onClick={handleResend}
            className="text-[#4648D4] text-sm font-medium mt-1 hover:underline cursor-pointer"
          >
            Renvoyer le code
          </button>
        ) : (
          <p className="text-[#444651]/50 text-sm mt-1">
            Renvoyer dans {resendTimer}s
          </p>
        )}

        {/* ✅ Added `group` to Link so group-hover works on the SVG inside it */}
        <Link href="/login" className="group text-[#444651] text-sm font-light hover:underline mt-6 flex justify-center items-center gap-1">
          <span className="group-hover:-translate-x-1 transition-transform duration-200">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 12H5M12 19l-7-7 7-7"/>
            </svg>
          </span>
          Retour à la connexion
        </Link>
      </div>
    </div>
  )
}