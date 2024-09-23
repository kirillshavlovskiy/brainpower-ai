module.exports = function override(config, env) {
  // ... other configurations
  config.output.publicPath = '/static/';
  return config;
}