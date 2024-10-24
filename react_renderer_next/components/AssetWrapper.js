// components/AssetWrapper.js
import { useRouter } from 'next/router';

export default function AssetWrapper({ children }) {
  const router = useRouter();
  const basePath = process.env.NEXT_PUBLIC_BASE_URL || '';

  return (
    <div data-base-path={basePath}>
      {children}
    </div>
  );
}