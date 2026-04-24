/** @type {import('jest').Config} */
const config = {
    testEnvironment: 'jsdom',
    setupFilesAfterEnv: ['<rootDir>/jest.setup.tsx'], // ✅ .tsx not .ts
    transform: {
        '^.+\\.(ts|tsx)$': ['ts-jest', {
            tsconfig: { jsx: 'react-jsx' },
        }],
    },
    moduleNameMapper: {
        '^@/(.*)$': '<rootDir>/$1',
        '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    },
    testMatch: [
        '**/__tests__/**/*.test.(ts|tsx)',
        '**/*.test.(ts|tsx)',
    ],
    collectCoverageFrom: [
        'pages/**/*.{ts,tsx}',
        'components/**/*.{ts,tsx}',
        '!pages/_app.tsx',
        '!pages/_document.tsx',
    ],
};

module.exports = config;