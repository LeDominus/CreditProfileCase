import type { ReactNode } from 'react'

import { Providers } from '@/fsd/app/providers/providers'
import '@/fsd/app/styles/globals.css'

/**
 * Shared html/body shell for every root layout (the app has several route
 * groups: (auth), (client), (bank) — each with its own root layout that
 * renders this shell). Fonts are self-hosted via @font-face in globals.css.
 */
export function RootShell({ children }: { children: ReactNode }) {
  return (
    <html lang="ru" className="h-full">
      <body className="min-h-full">
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
