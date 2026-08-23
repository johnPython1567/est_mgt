# est_mgt
An estate management

-pip freeze will get the dependencies that the project runs on
-pip freeze > requirements.txt will save the dependencies into requirement.txt

-User
 │
 ├── Property
 │     ├── Property Image
 │     ├── Property Feature
 │     └── Property Location
 │
 ├── Inquiry
 │
 └── Favorite

 Property
├── title
├── slug
├── description
├── property_type
├── listing_type
├── price
├── bedrooms
├── bathrooms
├── area
├── address
├── city
├── state
├── featured
├── is_published
├── created_at
└── updated_at

integrating tailwind with django.
step1: in your current project directory run mkdir frontend(or any name)

step2: cd to newly created folder and npm init -y(this will create package.json)

step3: run npm install -D vite tailwindcss @tailwindcss/vite to install tailwind and vite

step4: run npm list --depth=0 to check installation

step5: create vite.config.js inside frontend(any folder of your choice)
add 
    import { defineConfig } from "vite";
    import tailwindcss from "@tailwindcss/vite";

    export default defineConfig({
        plugins: [
            tailwindcss(),
        ],
    });

step5: create source folders inside of the frontend folder run
    mkdir src
    mkdir src\css
    mkdir src\js

    frontend/
        │
        ├── src/
        │   ├── css/
        │   └── js/
        │
        ├── package.json
        ├── package-lock.json
        └── vite.config.js

3. Create Tailwind input file
        frontend/src/css/input.css
        put this inside(@import "tailwindcss";)

Change code
   ↓
git status
   ↓
git add
   ↓
git commit
   ↓
git push
