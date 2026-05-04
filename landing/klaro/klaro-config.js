/* Klaro consent manager config — bodenbericht.de
 *
 * Services (granular, EDPB Guidelines 03/2022 §§ 95–103: getrennte Zwecke = getrennter Toggle):
 *   - google-analytics-4 : Traffic-Statistik (anonymisiert), via GTM-Bootstrap
 *   - posthog            : Produkt-Analytik + Session-Replay, via GTM-Bootstrap
 *
 * GTM ist der gemeinsame Bootstrap-Loader (`landing/index.html:10-16`); welcher
 * Tag innerhalb von GTM tatsächlich feuert, hängt vom `klaro-consent`-Cookie
 * + GTM-internen Trigger-Variablen ab. Klaro setzt für jeden akzeptierten
 * Service ein Cookie `klaro` mit dem Service-Namen, GTM liest das aus.
 *
 * Wenn der Nutzer GA4 akzeptiert aber PostHog ablehnt, lädt GTM also nur
 * GA4 — die granulare Wahl wird erst innerhalb GTM durchgesetzt. Dafür
 * werden die GTM-Trigger entsprechend konfiguriert.
 */
window.klaroConfig = {
    version: 2,
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
                    "Wir nutzen pseudonymisierte Analyse-Tools (Google Analytics 4 für Traffic-Statistik, PostHog für Nutzungs-Analyse mit Session-Aufzeichnungen), um unser Angebot zu verbessern. Sie können jeden Dienst getrennt akzeptieren oder ablehnen — Ihre Einwilligung ist freiwillig und jederzeit widerrufbar.",
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
                        "Erfassen pseudonymisierter Nutzungsdaten (Seitenaufrufe, Klicks, Scrolltiefe) zur Verbesserung der Website."
                },
                "session-replay": {
                    title: "Session-Aufzeichnung",
                    description:
                        "Pseudonymisierte Aufzeichnung Ihrer Mausbewegungen, Klicks und Scrolls auf der Seite, um Bedienprobleme zu erkennen. Eingaben in Formularfeldern werden ausgeschlossen."
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
            // Orchestrator: lädt den GTM-Container. GTM selbst sammelt KEINE
            // Daten, sondern triggert intern die Tags für GA4/PostHog --
            // diese Tags müssen IM GTM-UI so konfiguriert sein, dass sie nur
            // feuern, wenn das `klaro`-Cookie den jeweiligen Service-Namen
            // ("google-analytics-4" / "posthog") enthält. Dadurch bleibt
            // granulare Einwilligung erhalten, auch wenn nur einer der beiden
            // akzeptiert wurde.
            //
            // Damit GTM beim Akzeptieren JEDES der beiden Analyse-Dienste
            // lädt, ist dieser Eintrag mit `default: false` markiert -- Klaro
            // bietet ihn dem Nutzer als eigenen Toggle nicht an (per
            // `contextualConsentOnly: true`), aktiviert ihn aber automatisch,
            // wenn GA4 ODER PostHog akzeptiert werden (siehe Watcher in
            // `landing/static/landing-tracking.js`, der Klaro-Updates
            // beobachtet und ggf. den Manager-Status nachzieht).
            name: "google-tag-manager",
            title: "Google Tag Manager",
            description:
                "Technischer Orchestrator zum Laden der oben gewählten Analyse-Dienste. Sammelt selbst keine Daten.",
            purposes: ["analytics"],
            required: false,
            optOut: false,
            onlyOnce: true,
            contextualConsentOnly: true
        },
        {
            name: "google-analytics-4",
            title: "Google Analytics 4",
            description:
                "Erfasst pseudonymisierte Nutzungsdaten (Seitenaufrufe, Traffic-Quellen, Verweildauer). IP-Adressen werden gekürzt verarbeitet (Anonymize-IP). Anbieter: Google Ireland Ltd. (EU-US Data Privacy Framework zertifiziert).",
            purposes: ["analytics"],
            cookies: [
                [/^_ga/, "/", ".bodenbericht.de"],
                [/^_gid/, "/", ".bodenbericht.de"],
                [/^_gat/, "/", ".bodenbericht.de"]
            ],
            required: false,
            optOut: false,
            onlyOnce: true
        },
        {
            name: "posthog",
            title: "PostHog (EU)",
            description:
                "Pseudonymisierte Produkt-Analytik mit Session-Replay (Mausspuren + Klicks; keine Formular-Eingaben). Anbieter: PostHog Inc., Hosting in der EU (Frankfurt).",
            purposes: ["session-replay"],
            cookies: [
                [/^ph_/, "/", ".bodenbericht.de"]
            ],
            required: false,
            optOut: false,
            onlyOnce: true
        }
    ]
};
