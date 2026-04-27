"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  LayoutGrid,
  Users,
  UsersRound,
  FileText,
  UserCheck,
  CheckSquare,
  Award,
  Settings,
  LogOut,
} from "lucide-react"
import { cn } from "@/lib/utils"

interface SideBarProps {
  role?: "admin" | "user"
}

const adminMenuItems = [
  { icon: LayoutGrid, label: "Tableau de Bord", href: "/admin" },
  { icon: Users, label: "Utilisateurs", href: "/admin/utilisateurs" },
  { icon: UsersRound, label: "Équipes", href: "/admin/equipes" },
  { icon: FileText, label: "Sujets", href: "/admin/sujets" },
  { icon: UserCheck, label: "Phase de Choix", href: "/admin/phase-choix" },
  { icon: CheckSquare, label: "Affectation", href: "/admin/affectation" },
  { icon: Award, label: "Soutenances", href: "/admin/soutenances" },
]

export default function SideBar({ role = "admin" }: SideBarProps) {
  const pathname = usePathname()

  const menuItems = role === "admin" ? adminMenuItems : adminMenuItems

  return (
    <aside className="flex h-screen w-60 flex-col border-r border-slate-200 bg-white">
      {/* Logo */}
      <div className="flex h-16 items-center px-6">
        <Link href="/" className="text-xl font-bold text-[#0B1C30]">
          GradEX
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4">
        <ul className="space-y-1">
          {menuItems.map((item) => {
            const isActive = pathname === item.href || 
              (item.href !== "/admin" && pathname.startsWith(item.href))
            
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-emerald-50 text-emerald-600"
                      : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                  )}
                >
                  <item.icon className={cn("h-5 w-5", isActive ? "text-emerald-600" : "text-slate-400")} />
                  {item.label}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Footer Actions */}
      <div className="border-t border-slate-200 px-3 py-4">
        <ul className="space-y-1">
          <li>
            <Link
              href="/admin/parametres"
              className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-50 hover:text-slate-900"
            >
              <Settings className="h-5 w-5 text-slate-400" />
              Paramètres
            </Link>
          </li>
          <li>
            <button
              className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-emerald-600 transition-colors hover:bg-emerald-50"
            >
              <LogOut className="h-5 w-5" />
              Déconnexion
            </button>
          </li>
        </ul>
      </div>
    </aside>
  )
}

