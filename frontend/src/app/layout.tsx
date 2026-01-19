import "./globals.css";

export const metadata = {
  title: "Splendor 人机对战",
  description: "Splendor human-vs-AI web UI",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh">
      <body>{children}</body>
    </html>
  );
}
