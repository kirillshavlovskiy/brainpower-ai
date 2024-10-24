// pages/_app.js
import AssetWrapper from '../components/AssetWrapper';

function MyApp({ Component, pageProps }) {
  return (
    <AssetWrapper>
      <Component {...pageProps} />
    </AssetWrapper>
  );
}

export default MyApp;