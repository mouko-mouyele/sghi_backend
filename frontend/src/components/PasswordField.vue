<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: 'Mot de passe' },
  minlength: { type: [Number, String], default: undefined },
  required: { type: Boolean, default: false },
  id: { type: String, default: undefined },
  autocomplete: { type: String, default: 'current-password' },
})

const emit = defineEmits(['update:modelValue'])

const show = ref(false)
const inputType = computed(() => (show.value ? 'text' : 'password'))

function onInput(e) {
  emit('update:modelValue', e.target.value)
}
</script>

<template>
  <div class="relative">
    <input
      :id="id"
      :value="modelValue"
      :type="inputType"
      class="input-field pr-11"
      :placeholder="placeholder"
      :minlength="minlength"
      :required="required"
      :autocomplete="autocomplete"
      @input="onInput"
    />
    <button
      type="button"
      class="absolute right-3 top-1/2 -translate-y-1/2 rounded p-1 text-slate-400 dark:text-slate-500 hover:text-slate-700 dark:text-slate-300 dark:hover:text-slate-200"
      :aria-label="show ? 'Masquer le mot de passe' : 'Afficher le mot de passe'"
      @click="show = !show"
    >
      <svg v-if="!show" xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
      </svg>
      <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858 3.029a3 3 0 114.243-4.243m-4.242 4.242L5.46 5.46m0 0L3 3m2.46 2.46l16.97 16.97M21 21l-2.46-2.46" />
      </svg>
    </button>
  </div>
</template>
