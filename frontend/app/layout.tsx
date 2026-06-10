import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "个人内容消化平台",
  description: "动态个人信息加工操作系统"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
