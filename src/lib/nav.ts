// lib/nav.ts
import type { ComponentType } from 'react'
import {
  LayoutDashboard,
  FileText,
  Users,
  GitPullRequest,
  CheckSquare,
  Package,
  Bell,
  BookOpen,
  ClipboardList,
} from 'lucide-react'

export type Role = 'enseignant' | 'etudiant' | 'admin'

export type NavItem = {
  label: string
  href: string
  icon: ComponentType<{ size?: number; strokeWidth?: number; className?: string }>
}

export const navConfig: Record<Role, NavItem[]> = {
  enseignant: [
    { label: 'Dashboard',                href: '/dashboard',    icon: LayoutDashboard },
    { label: 'Gestion des Sujets',       href: '/sujets',       icon: FileText        },
    { label: 'Consultation des Équipes', href: '/equipes',      icon: Users           },
    { label: 'Demande de Changement',    href: '/changements',  icon: GitPullRequest  },
    { label: 'Gestion des Tâches',       href: '/taches',       icon: CheckSquare     },
    { label: 'Livrables',               href: '/livrables',    icon: Package         },
    { label: 'Notifications',           href: '/notifications', icon: Bell            },
  ],
  etudiant: [
    { label: 'Dashboard',               href: '/dashboard',    icon: LayoutDashboard },
    { label: 'Mes Sujets',              href: '/sujets',       icon: BookOpen        },
    { label: 'Mon Équipe',              href: '/equipes',      icon: Users           },
    { label: 'Mes Tâches',             href: '/taches',       icon: CheckSquare     },
    { label: 'Livrables',              href: '/livrables',    icon: Package         },
    { label: 'Notifications',          href: '/notifications', icon: Bell            },
  ],
  admin: [
    { label: 'Dashboard',              href: '/dashboard',    icon: LayoutDashboard },
    { label: 'Tous les Sujets',        href: '/sujets',       icon: ClipboardList   },
    { label: 'Utilisateurs',           href: '/utilisateurs', icon: Users           },
    { label: 'Notifications',          href: '/notifications', icon: Bell           },
  ],
}

export const ctaConfig: Record<Role, { label: string; href: string } | null> = {
  enseignant: { label: 'Nouveau Sujet',      href: '/sujets/nouveau'       },
  etudiant:   null,
  admin:      { label: 'Nouvel Utilisateur', href: '/utilisateurs/nouveau' },
}