import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { initTheme } from './composables/useTheme.js'
import inputFilter from './directives/inputFilter.js'
import './style.css'

initTheme()

createApp(App).use(router).directive('input-filter', inputFilter).mount('#app')
