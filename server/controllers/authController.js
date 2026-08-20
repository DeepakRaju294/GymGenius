const User = require('../models/userModel');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');

// docs/SPEC.md §6 - matches the {success, data|message} envelope every other
// controller uses; this file previously used {error} on failure and a bare
// {token, user} on success, which silently broke error display client-side
// (Login.js/Register.js were already reading err.response.data.message, which
// authController never sent).
function friendlyMessage(err) {
  if (err.code === 11000) {
    const field = Object.keys(err.keyPattern || {})[0] || 'value';
    return `That ${field} is already taken.`;
  }
  return err.message;
}

exports.register = async (req, res) => {
  try {
    const { username, email, password } = req.body;
    const hash = await bcrypt.hash(password, 10);
    await User.create({ username, email, password: hash });
    res.status(201).json({ success: true, message: 'User registered successfully' });
  } catch (err) {
    const status = err.code === 11000 || err.name === 'ValidationError' ? 400 : 500;
    res.status(status).json({ success: false, message: friendlyMessage(err) });
  }
};

exports.login = async (req, res) => {
  try {
    const { username, password } = req.body;
    const user = await User.findOne({ username });
    if (!user) return res.status(400).json({ success: false, message: 'Invalid credentials' });

    const match = await bcrypt.compare(password, user.password);
    if (!match) return res.status(400).json({ success: false, message: 'Invalid credentials' });

    const token = jwt.sign({ id: user._id, username: user.username }, process.env.JWT_SECRET, { expiresIn: '1h' });
    res.json({ success: true, data: { token, user: { id: user._id, username: user.username, email: user.email } } });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
};

exports.logout = async (req, res) => {
  // Stateless JWT - there is nothing to invalidate server-side. This exists so the
  // client has a real endpoint to call instead of only clearing localStorage.
  res.status(200).json({ success: true, message: 'Logged out' });
};
