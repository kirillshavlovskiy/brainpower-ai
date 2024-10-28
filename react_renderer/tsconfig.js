{
  "compilerOptions": {
      "baseUrl": ".",
        "paths": {
          "@/*": ["./*"]
        }
        "target": "es5",
        "lib": ["dom", "dom.iterable", "esnext"],
        "allowJs": true,
        "skipLibCheck": true,
        "esModuleInterop": true,
        "allowSyntheticDefaultImports": true,
        "strict": true,
        "forceConsistentCasingInFileNames": true,
        "noFallthroughCasesInSwitch": true,
        "module": "esnext",
        "moduleResolution": "node",
        "resolveJsonModule": true,
        "isolatedModules": true,
        "noEmit": false,
        "jsx": "react-jsx",

        "outDir": "./dist",
        "sourceMap": true,
        "declaration": true,
        "incremental": true
  },
  "include": ["src/**/*"],
  "exclude": [
    "node_modules",
    "build",
    "dist",
    "scripts",
    "webpack.config.js"
  ]
}