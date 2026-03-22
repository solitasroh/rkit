/**
 * @mcukit/wpf - WPF Domain Module Entry Point
 * @module lib/wpf
 * @version 0.4.0
 */
module.exports = {
  ...require('./xaml-analyzer'),
  ...require('./mvvm-validator'),
};
