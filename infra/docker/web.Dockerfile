# syntax=docker/dockerfile:1
# clusius-web for Cloud Run: Next.js standalone output, built with the API URL baked
# in at build time (NEXT_PUBLIC_* vars are inlined into the client bundle by Next.js,
# so this must be passed as a build arg, not a runtime env var).
FROM node:22-slim AS build

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install

COPY . .
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
RUN npm run build

FROM node:22-slim AS runtime

WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/public ./public
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static

EXPOSE 8080
ENV PORT=8080
CMD ["node", "server.js"]
