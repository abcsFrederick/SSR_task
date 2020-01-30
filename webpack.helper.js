module.exports = function (config) {
    config.module.rules.push({
        resource: {
            test: /\.scss$/,
            exclude: [/node_modules/]
        },
        use:[{
                loader: "style-loader" // creates style nodes from JS strings
            }, {
                loader: "css-loader" // translates CSS into CommonJS
            }, {
                loader: "sass-loader" // compiles Sass to CSS
            }]
    });
    config.module.rules.push({
        resource: {
            test: /\.js$/   ///node_modules(\/|\\)dicom-parser\.js(\/|\\).*.js$/,
         //   include: //[/node_modules(\/|\\)dicom-parser\.js(\/|\\)/]
        },
        use: [
            {
                loader: 'babel-loader',
                options: {
                    presets: ['env']
                }
            }
        ]
    });
    config.module.rules.push({
        resource: {
            test: /\.(html)$/,
        },
        use: [{
                loader: 'html-loader',
                options: {
                  attrs: [':data-src']
                }
              }]    
    });
    config.module.rules.push({
        resource: {
            test: /\.pug$/,//loader: 'babel-loader?presets[]=env!pug-loader'
        },
        use: [{
                loader: 'babel-loader',
                options: {
                  presets: ['env']
                }
              },
              {
                loader: 'pug-loader',               //chain loader to parse '`' by babel after parsing from pug-loader
              }]    
              
    });
    config.module.rules.push({
        
            test: /\.styl$/,
        
            loader: 'style-loader!css-loader!stylus-loader'
           
    });
    config.module.rules.push({
        
            test: /\.(jpe?g|png|gif|woff|woff2|eot|ttf|svg)(\?[a-z0-9=.]+)?$/,

            loader: 'url-loader?limit=100000' 
           
    });
    return config;
};