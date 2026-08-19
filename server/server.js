const dotenv = require('dotenv');
const mongoose = require('mongoose');
const app = require('./app');

dotenv.config({path: './config.env'});

mongoose
    .connect(process.env.MONGO_URI)
    .then(() => {
        app.listen(process.env.PORT || 5000, () => {
            console.log(`Server is running in port ${process.env.PORT}`)
    })})
    .catch(
        err => console.log(err)
    );
