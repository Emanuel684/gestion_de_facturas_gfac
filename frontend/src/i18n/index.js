import i18n from 'i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import { initReactI18next } from 'react-i18next';

import esCommon from './locales/es/common.json';
import enCommon from './locales/en/common.json';
import esAuth from './locales/es/auth.json';
import enAuth from './locales/en/auth.json';
import esLanding from './locales/es/landing.json';
import enLanding from './locales/en/landing.json';
import esNavbar from './locales/es/navbar.json';
import enNavbar from './locales/en/navbar.json';
import esUsers from './locales/es/users.json';
import enUsers from './locales/en/users.json';
import esBilling from './locales/es/billing.json';
import enBilling from './locales/en/billing.json';
import esDashboard from './locales/es/dashboard.json';
import enDashboard from './locales/en/dashboard.json';
import esReports from './locales/es/reports.json';
import enReports from './locales/en/reports.json';
import esInvoices from './locales/es/invoices.json';
import enInvoices from './locales/en/invoices.json';
import esPlatform from './locales/es/platform.json';
import enPlatform from './locales/en/platform.json';
import esOrganizations from './locales/es/organizations.json';
import enOrganizations from './locales/en/organizations.json';
import esModals from './locales/es/modals.json';
import enModals from './locales/en/modals.json';
import esTraceability from './locales/es/traceability.json';
import enTraceability from './locales/en/traceability.json';

const resources = {
  es: {
    common: esCommon,
    auth: esAuth,
    landing: esLanding,
    navbar: esNavbar,
    users: esUsers,
    billing: esBilling,
    dashboard: esDashboard,
    reports: esReports,
    invoices: esInvoices,
    platform: esPlatform,
    organizations: esOrganizations,
    modals: esModals,
    traceability: esTraceability,
  },
  en: {
    common: enCommon,
    auth: enAuth,
    landing: enLanding,
    navbar: enNavbar,
    users: enUsers,
    billing: enBilling,
    dashboard: enDashboard,
    reports: enReports,
    invoices: enInvoices,
    platform: enPlatform,
    organizations: enOrganizations,
    modals: enModals,
    traceability: enTraceability,
  },
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'en',
    supportedLngs: ['es', 'en'],
    defaultNS: 'common',
    interpolation: { escapeValue: false },
    detection: {
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: 'sgf_lang',
      caches: ['localStorage'],
    },
    nonExplicitSupportedLngs: true,
  });

export default i18n;
