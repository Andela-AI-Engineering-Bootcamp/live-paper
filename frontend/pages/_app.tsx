import type { AppProps } from 'next/app';
import dynamic from 'next/dynamic';
import '../styles/globals.css';

// Client-side only — avoids SSR errors during `next build` with `output: export`
const ClerkProviderNoSSR = dynamic(
  () => import('@clerk/nextjs').then((m) => ({ default: m.ClerkProvider })),
  { ssr: false }
);

export default function MyApp({ Component, pageProps }: AppProps) {
  return (
    <ClerkProviderNoSSR {...pageProps}>
      <Component {...pageProps} />
    </ClerkProviderNoSSR>
  );
}