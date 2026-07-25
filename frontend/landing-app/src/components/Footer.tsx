import { supportLinks } from "../data";

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <div className="footer-logo">
            <span className="logo-icon" style={{width: 36, height: 36, fontSize: 18}}>P</span>
            <span className="logo-text"><span style={{color:"#708498"}}>PROP</span><span style={{color:"#95A58F"}}>AURA</span></span>
          </div>
          <p className="footer-tagline">
            &nbsp;
          </p>
        </div>

        <div className="footer-col">
          <h4 className="footer-heading">Features</h4>
          <ul>
            <li><a href="#features">Rent Collection</a></li>
            <li><a href="#features">Tenant Management</a></li>
            <li><a href="#features">Smart Alerts</a></li>
            <li><a href="#features">Receipts</a></li>
          </ul>
        </div>

        <div className="footer-col">
          <h4 className="footer-heading">Support</h4>
          <ul>
            {supportLinks.map((link) => (
              <li key={link}><a href="#">{link}</a></li>
            ))}
          </ul>
        </div>

        <div className="footer-col">
          <h4 className="footer-heading">Contact</h4>
          <ul>
            <li><a href="mailto:vijaykrsha@hotmail.com">vijaykrsha@hotmail.com</a></li>
            <li><a href="tel:+919449825584">+91 94498 25584</a></li>
          </ul>
        </div>
      </div>

      <div className="footer-bottom">
        <p>&copy; {new Date().getFullYear()} PROPAURA. All rights reserved.</p>
        <div className="footer-bottom-links">
          <a href="#">Privacy Policy</a>
          <a href="#">Terms of Service</a>
        </div>
      </div>
    </footer>
  );
}
