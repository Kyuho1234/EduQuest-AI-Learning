import { Inter } from 'next/font/google'
import './globals.css'
import type { Metadata } from 'next'
import { AppRouterCacheProvider } from '@mui/material-nextjs/v13-appRouter';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import theme from '@/src/theme';

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'EduQuest - AI 학습 시스템',
  description: '인공지능을 활용한 교육용 문제 생성 및 학습 지원 시스템',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ko">
      <body className={inter.className}>
        <AppRouterCacheProvider>
          <ThemeProvider theme={theme}>
            <CssBaseline />
            {children}
          </ThemeProvider>
        </AppRouterCacheProvider>
      </body>
    </html>
  )
}