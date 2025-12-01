const path = require('path');
const nodeExternals = require('webpack-node-externals');

module.exports = function (options, webpack) {
  return {
    ...options,
    externals: [
      // Externalize all node_modules except workspace packages
      nodeExternals({
        allowlist: ['@time-tracker/shared'],
        modulesFromFile: true,
      }),
      // Explicitly externalize bcrypt and its dependencies
      'bcrypt',
      '@mapbox/node-pre-gyp',
    ],
    output: {
      ...options.output,
      libraryTarget: 'commonjs2',
    },
    resolve: {
      ...options.resolve,
      fallback: {
        ...options.resolve?.fallback,
        'nock': false,
        'aws-sdk': false,
        'mock-aws-s3': false,
      },
    },
    module: {
      ...options.module,
      rules: [
        ...options.module.rules,
        {
          test: /\.html$/,
          type: 'asset/source',
        },
      ],
      // Ignore problematic dynamic requires
      exprContextCritical: false,
    },
    ignoreWarnings: [
      /Critical dependency: the request of a dependency is an expression/,
    ],
  };
};
