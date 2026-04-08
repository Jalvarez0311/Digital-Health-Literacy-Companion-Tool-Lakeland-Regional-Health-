/* ============================================================
   Lakeland Regional Health — Accessibility Manager
   Handles: language, color-vision, contrast/dark mode, TTS
   All preferences persisted in localStorage.
   ============================================================ */



const A11Y = (() => {

  /* ── Keys ──────────────────────────────────────────────── */
  const KEYS = {
    lang:     'lrh_lang',
    vision:   'lrh_vision',
    theme:    'lrh_theme',
    tts:      'lrh_tts',
  };

  /* ── Translations ──────────────────────────────────────── */
  const T = {
    en: {
      'nav.settings':        'Accessibility',
      'nav.back':            '← Back',
      'nav.logout':          'Logout',
      'welcome.heading':     'Welcome to the Digital Health Literacy Companion Tool!',
      'welcome.sub':         'Please select your role to continue.',
      'role.nurse':          'I am a Nurse',
      'role.patient':        'I am a Patient',
      'login.heading':       'Sign In',
      'login.sub':           'Enter your credentials to access your portal.',
      'login.username':      'Username',
      'login.password':      'Password',
      'login.forgot':        'Forgot Password?',
      'login.submit':        'Sign In',
      'login.noaccount':     "Don't have an account?",
      'login.signup':        'Create one here',
      'login.error':         'Invalid username or password. Please try again.',
      'signup.heading':      'Create Account',
      'signup.sub':          'Register to access the Health Companion portal.',
      'signup.submit':       'Create Account',
      'signup.success':      'Account created! Redirecting to login…',
      'dash.nurse.heading':  'Nurse Dashboard',
      'dash.nurse.sub':      'Select an action below to get started.',
      'dash.patient.heading':'Patient Dashboard',
      'dash.patient.sub':    'What would you like to do today?',
      'card.discharge':      'Create Discharge Summary',
      'card.survey':         'Take Survey',
      'card.patientinfo':    'View Patient Info',
      'settings.title':      'Accessibility Settings',
      'settings.lang':       'Language',
      'settings.vision':     'Color Vision Mode',
      'settings.theme':      'Display Theme',
      'settings.tts':        'Text-to-Speech',
      'settings.save':       'Save Settings',
      'settings.saved':      'Settings saved!',
      'vision.normal':       'Default',
      'vision.deuteranopia': 'Deuteranopia (Red-Green)',
      'vision.protanopia':   'Protanopia (Red Deficiency)',
      'vision.tritanopia':   'Tritanopia (Blue-Yellow)',
      'vision.monochromacy': 'Monochromacy (Greyscale)',
      'theme.default':       'Default',
      'theme.dark':          'Dark Mode',
      'theme.high-contrast': 'High Contrast',
      'tts.off':             'Off',
      'tts.on':              'On — reads page aloud on load',
      'footer.copy':         '© 2026 Lakeland Regional Health · All rights reserved',
    },
    es: {
      'nav.settings':        'Accesibilidad',
      'nav.back':            '← Regresar',
      'nav.logout':          'Cerrar sesión',
      'welcome.heading':     '¡Bienvenido a la herramienta complementaria de alfabetización en salud digital!',
      'welcome.sub':         'Por favor seleccione tu rol para continuar.',
      'role.nurse':          'Soy Enfermera/o',
      'role.patient':        'Soy Paciente',
      'login.heading':       'Iniciar sesión',
      'login.sub':           'Ingrese sus credenciales para acceder al portal.',
      'login.username':      'Usuario',
      'login.password':      'Contraseña',
      'login.forgot':        '¿Olvidó su contraseña?',
      'login.submit':        'Iniciar sesión',
      'login.noaccount':     '¿No tiene cuenta?',
      'login.signup':        'Crea una aquí',
      'login.error':         'usuario o contraseña es incorrecto. Intente de nuevo.',
      'signup.heading':      'Crear cuenta',
      'signup.sub':          'Regístrese para acceder al portal.',
      'signup.submit':       'Crear cuenta',
      'signup.success':      '¡Cuenta creada! Redirigiendo al inicio de sesión…',
      'dash.nurse.heading':  'Panel de enfermería',
      'dash.nurse.sub':      'Seleccione una opción para continuar.',
      'dash.patient.heading':'Panel del paciente',
      'dash.patient.sub':    '¿Qué desea hacer hoy?',
      'card.discharge':      'Crear resumen de alta',
      'card.survey':         'Responder encuesta',
      'card.patientinfo':    'Ver información del paciente',
      'settings.title':      'Configuración de accesibilidad',
      'settings.lang':       'Idioma',
      'settings.vision':     'Modo de visión de color',
      'settings.theme':      'Tema de pantalla',
      'settings.tts':        'Texto a voz',
      'settings.save':       'Guardar configuración',
      'settings.saved':      '¡Configuración guardada!',
      'vision.normal':       'Predeterminado',
      'vision.deuteranopia': 'Deuteranopía (Rojo-Verde)',
      'vision.protanopia':   'Protanopía (Deficiencia de rojo)',
      'vision.tritanopia':   'Tritanopía (Azul-Amarillo)',
      'vision.monochromacy': 'Monocromatismo (Escala de grises)',
      'theme.default':       'Predeterminado',
      'theme.dark':          'Modo oscuro',
      'theme.high-contrast': 'Alto contraste',
      'tts.off':             'Desactivado',
      'tts.on':              'Activado — Lee la página cuando carga',
      'footer.copy':         '© 2026 Lakeland Regional Health · Todos los derechos reservados',
    }
  };

  /* ── CSS filter maps for colour vision ─────────────────── */
  const VISION_FILTERS = {
    normal:       'none',
    deuteranopia: 'url(#deuteranopia)',
    protanopia:   'url(#protanopia)',
    tritanopia:   'url(#tritanopia)',
    monochromacy: 'grayscale(100%)',
  };

  /* ── SVG colour-blind filters injected once into the DOM ── */
  function injectSVGFilters() {
    if (document.getElementById('lrh-cvd-filters')) return;
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.id = 'lrh-cvd-filters';
    svg.setAttribute('style', 'position:absolute;width:0;height:0;overflow:hidden');
    svg.innerHTML = `
      <defs>
        <!-- Deuteranopia -->
        <filter id="deuteranopia">
          <feColorMatrix type="matrix" values="
            0.625 0.375 0     0 0
            0.7   0.3   0     0 0
            0     0.3   0.7   0 0
            0     0     0     1 0"/>
        </filter>
        <!-- Protanopia -->
        <filter id="protanopia">
          <feColorMatrix type="matrix" values="
            0.567 0.433 0     0 0
            0.558 0.442 0     0 0
            0     0.242 0.758 0 0
            0     0     0     1 0"/>
        </filter>
        <!-- Tritanopia -->
        <filter id="tritanopia">
          <feColorMatrix type="matrix" values="
            0.95  0.05  0     0 0
            0     0.433 0.567 0 0
            0     0.475 0.525 0 0
            0     0     0     1 0"/>
        </filter>
      </defs>`;
    document.body.prepend(svg);
  }

  /* ── Apply all stored preferences to <html> ────────────── */
  function applyAll() {
    const lang   = localStorage.getItem(KEYS.lang)   || 'en';
    const vision = localStorage.getItem(KEYS.vision) || 'normal';
    const theme  = localStorage.getItem(KEYS.theme)  || 'default';

    const html = document.documentElement;

    // Language attribute
    html.setAttribute('lang', lang === 'es' ? 'es' : 'en');
    html.setAttribute('data-lang', lang);

    // Vision filter on <body>
    injectSVGFilters();
    document.body.style.filter = VISION_FILTERS[vision] || 'none';

    // Theme class
    html.classList.remove('theme-dark', 'theme-high-contrast');
    if (theme === 'dark')          html.classList.add('theme-dark');
    if (theme === 'high-contrast') html.classList.add('theme-high-contrast');

    // Translate data-i18n elements
    translatePage(lang);

    // TTS
    if (localStorage.getItem(KEYS.tts) === 'on') {
      window.addEventListener('load', () => speakPage(), { once: true });
    }
  }

  /* ── Translate all [data-i18n] elements ─────────────────── */
function translatePage(lang) {
  const dict = T[lang] || T.en;
  console.log('Translating to language:', lang);
  console.log('Available translations:', dict);
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    console.log('Element with key:', key, 'current text:', el.textContent);
    if (key in dict) {
      const newText = dict[key];
      console.log('Translating', key, 'to:', newText);
      if (el.tagName === 'INPUT' && el.placeholder !== undefined) {
        el.placeholder = newText;
      } else {
        el.textContent = newText;
      }
      console.log('After translation:', el.textContent);
    } else {
      console.warn('Missing translation for', key);
    }
  });
}

  /* ── Text-to-Speech ─────────────────────────────────────── */
  function speakPage() {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();

    const lang = localStorage.getItem(KEYS.lang) || 'en';

    // Collect readable text nodes from main content
    const main = document.querySelector('main') || document.body;
    const text = (main.innerText || main.textContent || '').trim().replace(/\s+/g, ' ');
    if (!text) return;

    const utt = new SpeechSynthesisUtterance(text);
    utt.lang = lang === 'es' ? 'es-US' : 'en-US';
    utt.rate = 0.92;
    window.speechSynthesis.speak(utt);
  }

  function stopTTS() {
    if (window.speechSynthesis) window.speechSynthesis.cancel();
  }

  /* ── Public API ─────────────────────────────────────────── */
  return { applyAll, translatePage, speakPage, stopTTS, KEYS, T };
})();

/* Run on every page load */
document.addEventListener('DOMContentLoaded', () => A11Y.applyAll());