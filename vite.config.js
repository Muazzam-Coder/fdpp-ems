import { defineConfig } from 'vite'
import replace from '@rollup/plugin-replace'

export default defineConfig({
  plugins: [
    // Replace top-level module directives like "use client" in node_modules
    replace({
      include: /node_modules\/.*\\.mjs$/,
      preventAssignment: true,
      values: { '"use client"': '' }
    })
  ]
})
