/* Klaro consent manager config — bodenbericht.de
 * Docs: https://klaro.org/docs/
 *
 * Services:
 *   - google-tag-manager: lädt GTM (Container GTM-KFG5W96X), der wiederum GA4 + PostHog lädt.
 *
 * Hinweis: GA4 und PostHog sind in GTM als Tags konfiguriert; sie feuern nur,
 * wenn GTM selbst geladen ist — also nur nach Consent dieses einen Service-Eintrags.
 */
window.klaroConfig = {
    version: 1,
    elementID: "klaro",
    storageMethod: "cookie",
    storageName: "klaro-consent",
    cookieExpiresAfterDays: 365,

    default: false,
    mustConsent: false,
    acceptAll: true,
    hideDeclineAll: false,
    hideLearnMore: false,
    noticeAsModal: false,
    htmlTexts: true,
    lang: "de",

    translations: {
        de: {
            consentNotice: {
                title: "Cookies & Analyse",
                description:
                    "Wir nutzen anonymisierte Analyse-Tools (Google Analytics 4, PostHog), um die Nutzung unserer Website zu verstehen und das Angebot zu verbessern. Ihre Einwilligung ist freiwillig und jederzeit widerrufbar.",
                learnMore: "Details"
            },
            consentModal: {
                title: "Datenschutz-Einstellungen",
                description:
                    "Hier können Sie festlegen, welche Dienste wir auf dieser Website laden dürfen. Notwendige Funktionen der Website bleiben unabhängig von Ihrer Auswahl aktiv."
            },
            ok: "Alle akzeptieren",
            acceptAll: "Alle akzeptieren",
            acceptSelected: "Auswahl speichern",
            decline: "Ablehnen",
            save: "Speichern",
            close: "Schließen",
            poweredBy: "Weitere Informationen in der <a href='/datenschutz.html'>Datenschutzerklärung</a>.",
            purposes: {
                analytics: {
                    title: "Analyse",
                    description:
                        "Erfassen anonymisierter Nutzungsdaten (Seitenaufrufe, Klicks, Scrolltiefe, Sitzungs-Verlauf) zur Verbesserung der Website."
                }
            },
            service: {
                disableAll: {
                    title: "Alle Dienste ein-/ausschalten",
                    description: "Aktiviert oder deaktiviert alle Dienste auf einmal."
                },
                optOut: { title: "(Opt-out)", description: "" },
                required: { title: "(immer erforderlich)", description: "" },
                purpose: "Zweck",
                purposes: "Zwecke"
            }
        }
    },

    services: [
        {
            name: "google-tag-manager",
            title: "Google Tag Manager (GA4 + PostHog)",
            description:
                "Lädt Google Analytics 4 (Traffic-Quellen, Seitenaufrufe) und PostHog (Produkt-Analytik, Session-Aufzeichnungen). Daten werden anonymisiert verarbeitet, IP-Adressen gekürzt.",
            purposes: ["analytics"],
            cookies: [
                [/^_ga/, "/", ".bodenbericht.de"],
                [/^_gid/, "/", ".bodenbericht.de"],
                [/^_gat/, "/", ".bodenbericht.de"],
                [/^ph_/, "/", ".bodenbericht.de"]
            ],
            required: false,
            optOut: false,
            onlyOnce: true
        }
    ]
};
