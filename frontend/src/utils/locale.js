export function localeFromLanguage(language) {
  return language?.startsWith('en') ? 'en-US' : 'es-CO';
}
