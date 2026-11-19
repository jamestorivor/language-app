import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.tsx';
import { ClerkProvider } from '@clerk/chrome-extension';

const publishableKey = import.meta.env.WXT_CLERK_PUBLISHABLE_KEY;
const extensionUrl = browser.runtime.getURL('/');
import './style.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    {publishableKey ? <ClerkProvider publishableKey={publishableKey} afterSignOutUrl={extensionUrl} allowedRedirectProtocols={['chrome-extension:']}><App /></ClerkProvider> : <p>Configure WXT_CLERK_PUBLISHABLE_KEY to sign in.</p>}
  </React.StrictMode>,
);
