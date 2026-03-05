// Multi-language Support Module

const translations = {
    en: {
        // Navigation
        home: 'Home',
        dashboard: 'Dashboard',
        apply_pass: 'Apply for Pass',
        renew_pass: 'Renew Pass',
        trip_history: 'Trip History',
        payments: 'Payments',
        profile: 'Profile',
        logout: 'Logout',
        login: 'Login',
        register: 'Register',
        
        // Dashboard
        welcome: 'Welcome',
        active_pass: 'Active Pass',
        no_active_pass: 'No Active Pass',
        days_remaining: 'Days Remaining',
        recent_trips: 'Recent Trips',
        view_all: 'View All',
        
        // Pass types
        monthly_pass: 'Monthly Pass',
        quarterly_pass: 'Quarterly Pass',
        yearly_pass: 'Yearly Pass',
        
        // Status
        active: 'Active',
        expired: 'Expired',
        pending: 'Pending',
        completed: 'Completed',
        cancelled: 'Cancelled',
        
        // Actions
        apply_now: 'Apply Now',
        renew_now: 'Renew Now',
        show_qr: 'Show QR Code',
        download: 'Download',
        print: 'Print',
        share: 'Share',
        save: 'Save',
        cancel: 'Cancel',
        confirm: 'Confirm',
        
        // Messages
        pass_expiring_soon: 'Your pass is expiring soon',
        renew_to_continue: 'Renew now to continue uninterrupted service',
        payment_successful: 'Payment successful',
        payment_failed: 'Payment failed',
        
        // Form labels
        full_name: 'Full Name',
        email: 'Email Address',
        phone: 'Phone Number',
        address: 'Address',
        password: 'Password',
        confirm_password: 'Confirm Password',
        
        // Errors
        required_field: 'This field is required',
        invalid_email: 'Please enter a valid email address',
        invalid_phone: 'Please enter a valid phone number',
        password_mismatch: 'Passwords do not match',
        
        // Footer
        copyright: 'All rights reserved',
        privacy_policy: 'Privacy Policy',
        terms_of_service: 'Terms of Service',
        contact_us: 'Contact Us'
    },
    
    es: {
        // Navigation
        home: 'Inicio',
        dashboard: 'Panel',
        apply_pass: 'Solicitar Pase',
        renew_pass: 'Renovar Pase',
        trip_history: 'Historial',
        payments: 'Pagos',
        profile: 'Perfil',
        logout: 'Cerrar Sesión',
        login: 'Iniciar Sesión',
        register: 'Registrarse',
        
        // Dashboard
        welcome: 'Bienvenido',
        active_pass: 'Pase Activo',
        no_active_pass: 'Sin Pase Activo',
        days_remaining: 'Días Restantes',
        recent_trips: 'Viajes Recientes',
        view_all: 'Ver Todo',
        
        // Pass types
        monthly_pass: 'Pase Mensual',
        quarterly_pass: 'Pase Trimestral',
        yearly_pass: 'Pase Anual',
        
        // Status
        active: 'Activo',
        expired: 'Expirado',
        pending: 'Pendiente',
        completed: 'Completado',
        cancelled: 'Cancelado',
        
        // Actions
        apply_now: 'Solicitar Ahora',
        renew_now: 'Renovar Ahora',
        show_qr: 'Mostrar QR',
        download: 'Descargar',
        print: 'Imprimir',
        share: 'Compartir',
        save: 'Guardar',
        cancel: 'Cancelar',
        confirm: 'Confirmar',
        
        // Messages
        pass_expiring_soon: 'Tu pase está por expirar',
        renew_to_continue: 'Renueva ahora para continuar el servicio',
        payment_successful: 'Pago exitoso',
        payment_failed: 'Pago fallido',
        
        // Form labels
        full_name: 'Nombre Completo',
        email: 'Correo Electrónico',
        phone: 'Teléfono',
        address: 'Dirección',
        password: 'Contraseña',
        confirm_password: 'Confirmar Contraseña',
        
        // Errors
        required_field: 'Este campo es obligatorio',
        invalid_email: 'Ingrese un correo válido',
        invalid_phone: 'Ingrese un teléfono válido',
        password_mismatch: 'Las contraseñas no coinciden',
        
        // Footer
        copyright: 'Todos los derechos reservados',
        privacy_policy: 'Política de Privacidad',
        terms_of_service: 'Términos de Servicio',
        contact_us: 'Contáctenos'
    },
    
    fr: {
        // Navigation
        home: 'Accueil',
        dashboard: 'Tableau de bord',
        apply_pass: 'Demander un Pass',
        renew_pass: 'Renouveler',
        trip_history: 'Historique',
        payments: 'Paiements',
        profile: 'Profil',
        logout: 'Déconnexion',
        login: 'Connexion',
        register: 'S\'inscrire',
        
        // Dashboard
        welcome: 'Bienvenue',
        active_pass: 'Pass Actif',
        no_active_pass: 'Pas de Pass Actif',
        days_remaining: 'Jours Restants',
        recent_trips: 'Trajets Récents',
        view_all: 'Voir Tout',
        
        // Pass types
        monthly_pass: 'Pass Mensuel',
        quarterly_pass: 'Pass Trimestriel',
        yearly_pass: 'Pass Annuel',
        
        // Status
        active: 'Actif',
        expired: 'Expiré',
        pending: 'En attente',
        completed: 'Terminé',
        cancelled: 'Annulé',
        
        // Actions
        apply_now: 'Postuler',
        renew_now: 'Renouveler',
        show_qr: 'Afficher QR',
        download: 'Télécharger',
        print: 'Imprimer',
        share: 'Partager',
        save: 'Enregistrer',
        cancel: 'Annuler',
        confirm: 'Confirmer',
        
        // Messages
        pass_expiring_soon: 'Votre pass expire bientôt',
        renew_to_continue: 'Renouvelez maintenant',
        payment_successful: 'Paiement réussi',
        payment_failed: 'Paiement échoué',
        
        // Form labels
        full_name: 'Nom Complet',
        email: 'Adresse Email',
        phone: 'Téléphone',
        address: 'Adresse',
        password: 'Mot de passe',
        confirm_password: 'Confirmer',
        
        // Errors
        required_field: 'Ce champ est requis',
        invalid_email: 'Email invalide',
        invalid_phone: 'Téléphone invalide',
        password_mismatch: 'Mots de passe différents',
        
        // Footer
        copyright: 'Tous droits réservés',
        privacy_policy: 'Confidentialité',
        terms_of_service: 'Conditions d\'utilisation',
        contact_us: 'Contactez-nous'
    }
};

class Translator {
    constructor() {
        this.currentLang = localStorage.getItem('language') || 'en';
        this.translations = translations;
        this.init();
    }
    
    init() {
        this.translatePage();
        this.setupLanguageSelector();
    }
    
    translatePage() {
        document.querySelectorAll('[data-translate]').forEach(element => {
            const key = element.getAttribute('data-translate');
            const translation = this.getTranslation(key);
            if (translation) {
                if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                    element.placeholder = translation;
                } else {
                    element.textContent = translation;
                }
            }
        });
        
        // Update HTML lang attribute
        document.documentElement.lang = this.currentLang;
    }
    
    getTranslation(key) {
        const keys = key.split('.');
        let value = this.translations[this.currentLang];
        
        for (const k of keys) {
            if (value && value[k]) {
                value = value[k];
            } else {
                return key;
            }
        }
        
        return value;
    }
    
    setLanguage(lang) {
        if (this.translations[lang]) {
            this.currentLang = lang;
            localStorage.setItem('language', lang);
            this.translatePage();
            
            // Dispatch event for other components
            window.dispatchEvent(new CustomEvent('languageChanged', { detail: { language: lang } }));
        }
    }
    
    setupLanguageSelector() {
        const selector = document.getElementById('languageSelect');
        if (selector) {
            selector.value = this.currentLang;
            selector.addEventListener('change', (e) => {
                this.setLanguage(e.target.value);
            });
        }
    }
}

// Initialize translator
document.addEventListener('DOMContentLoaded', () => {
    window.translator = new Translator();
});

// Helper function to translate text dynamically
function __(key) {
    if (window.translator) {
        return window.translator.getTranslation(key);
    }
    return key;
}