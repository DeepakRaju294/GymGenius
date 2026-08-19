import { render, screen } from '@testing-library/react';
import App from './App';

test('renders the landing page after the auth check resolves', async () => {
  render(<App />);
  const heading = await screen.findByRole('heading', { name: /GymGenius/i });
  expect(heading).toBeInTheDocument();
});
