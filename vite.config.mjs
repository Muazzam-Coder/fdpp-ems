import { defineConfig } from 'vite'
import replace from '@rollup/plugin-replace'

export default defineConfig({
  // Avoid pre-bundling `sonner` which contains a top-level "use client" directive
  // so our replace plugin can strip it during the Rollup build step.
  optimizeDeps: {
    exclude: ['sonner']
  },
  plugins: [
    // Replace top-level module directives like "use client" in node_modules
    replace({
      // target both .mjs and .js files under node_modules
      include: /node_modules[\\/].*\.(?:mjs|js)$/,
      preventAssignment: true,
      // handle both single- and double-quoted directives
      values: {
        "'use client'": '',
        '"use client"': ''
      }
    })
  ]
})
