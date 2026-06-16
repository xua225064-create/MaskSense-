# Setup Guide: shadcn/ui, Tailwind CSS, & TypeScript

This guide outlines how to set up and configure your React project to fully support shadcn/ui components, Tailwind CSS styling, and TypeScript.

---

## 📁 1. Default Paths & Folder Structure

### Components & Styles Paths
- **Components Default Path:** `components/ui/` (mapped as `@/components/ui`)
  - This folder stores base UI primitives (buttons, inputs, grids) that are generic and reusable across the entire application.
- **Styles Default Path:** 
  - For **Next.js**: `app/globals.css` or `src/app/globals.css`
  - For **Vite/React**: `src/index.css` or `src/app.css`

### Why `/components/ui` is Critical
1. **shadcn/ui CLI Integration:** The shadcn CLI is pre-configured to download and update UI component primitives directly into `/components/ui`. Using a different path requires manual overrides in `components.json` and can break automated updates.
2. **Separation of Concerns:** It separates low-level reusable building blocks (e.g. custom button components, dialogs) from complex, stateful page-level components or layout structures.
3. **Path Alias Standard:** Standard configurations map `@/` to the project root or `src` folder. Mapping `@/components/ui/` allows clean, short import declarations (e.g. `import { Button } from "@/components/ui/button"`) which avoids messy relative imports like `../../components/ui/button`.

---

## 🚀 2. Step-by-Step Project Setup

If you are starting a new project or migrating an existing React project, follow these instructions to set up TypeScript, Tailwind CSS, and shadcn/ui.

### Step 2.1: Initialize a React Project with TypeScript

If starting fresh with **Vite** (recommended for SPA) or **Next.js** (recommended for SSR/Full Stack):

#### Option A: Next.js (App Router, TS, Tailwind)
```bash
npx create-next-app@latest my-app --typescript --tailwind --eslint --src-dir --app --import-alias "@/*"
cd my-app
```

#### Option B: Vite (React + TypeScript)
```bash
# Create Vite React-TS project
npm create vite@latest my-app -- --template react-ts
cd my-app

# Install dependencies
npm install
```

---

### Step 2.2: Set Up TypeScript (For Existing JavaScript Projects)

If you have a JavaScript project and want to migrate to TypeScript:

1. **Install TypeScript dependencies:**
   ```bash
   npm install -D typescript @types/react @types/react-dom @types/node
   ```

2. **Initialize tsconfig:**
   ```bash
   npx tsc --init
   ```

3. **Configure Path Aliases in `tsconfig.json`:**
   Add path mapping under `compilerOptions` so that imports like `@/components/*` point to the correct files:
   ```json
   {
     "compilerOptions": {
       "target": "ES2022",
       "module": "ESNext",
       "moduleResolution": "bundler",
       "baseUrl": ".",
       "paths": {
         "@/*": ["./*"] // Or ["./src/*"] if using a src directory
       },
       "jsx": "react-jsx",
       "strict": true,
       "esModuleInterop": true,
       "skipLibCheck": true
     }
   }
   ```

4. **Rename files:**
   Rename `.js` or `.jsx` files to `.ts` or `.tsx`.

---

### Step 2.3: Set Up Tailwind CSS

If Tailwind CSS is not yet installed in your React project:

1. **Install Tailwind CSS and its peer dependencies:**
   ```bash
   npm install -D tailwindcss postcss autoprefixer
   npx tailwindcss init -p
   ```

2. **Configure template paths in `tailwind.config.js`:**
   ```javascript
   /** @type {import('tailwindcss').Config} */
   export default {
     content: [
       "./index.html",
       "./src/**/*.{js,ts,jsx,tsx}",
       "./components/**/*.{js,ts,jsx,tsx}", // include components directory
       "./app/**/*.{js,ts,jsx,tsx}",       // include Next.js app directory
     ],
     theme: {
       extend: {},
     },
     plugins: [],
   }
   ```

3. **Add the Tailwind directives to your CSS file** (e.g., `src/index.css` or `app/globals.css`):
   ```css
   @tailwind base;
   @tailwind components;
   @tailwind utilities;
   ```

---

### Step 2.4: Setup shadcn/ui via CLI

1. **Initialize shadcn in your project:**
   Run the CLI init command to set up component paths, Tailwind configuration, and utility functions:
   ```bash
   npx shadcn@latest init
   ```

2. **Answer the CLI configuration prompts:**
   - **Style:** Default
   - **Base color:** Slate or Neutral
   - **CSS variables:** Yes
   - **Tailwind CSS configuration file location:** `tailwind.config.js` (or `tailwind.config.ts`)
   - **Import alias for components:** `@/components`
   - **Import alias for utils:** `@/lib/utils`
   - **React Server Components (RSC) support:** Yes (if Next.js) / No (if Vite/React)
   - **Write configuration to `components.json`:** Yes

3. **Use shadcn to add components:**
   Once initialized, you can add pre-styled components (like button, input, card, etc.) instantly:
   ```bash
   npx shadcn@latest add button
   npx shadcn@latest add dialog
   ```

---

## 🛠️ 3. Adding and Running "The Infinite Grid"

We have already integrated the component and demo files in your project:
- `/components/ui/the-infinite-grid.tsx`
- `/components/ui/demo.tsx`
- `/lib/utils.ts`

### 1. Install framer-motion (Completed)
```bash
npm install framer-motion clsx tailwind-merge
```

### 2. Standard CSS Custom Properties
Ensure your global CSS file (e.g. `index.css` or `globals.css`) defines standard shadcn variables so that colors resolve properly:
```css
@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --primary: 222.2 47.4% 11.2%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
  }
  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    --primary: 210 40% 98%;
    --primary-foreground: 222.2 47.4% 11.2%;
    --secondary: 217.2 32.6% 17.5%;
    --secondary-foreground: 210 40% 98%;
    --muted: 217.2 32.6% 17.5%;
    --muted-foreground: 215 20.2% 65.1%;
  }
}
```
