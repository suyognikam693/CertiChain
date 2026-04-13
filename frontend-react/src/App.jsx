import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Landing from './pages/Landing';
import University from './pages/University';
import UniversityIssue from './pages/UniversityIssue';
import UniversityRevoke from './pages/UniversityRevoke';
import Student from './pages/Student';
import Employer from './pages/Employer';
import StudentLogin from './pages/StudentLogin';
import UniversityLogin from './pages/UniversityLogin';
import VerifySuccess from './pages/VerifySuccess';
import VerifyFailed from './pages/VerifyFailed';
import PixelBlast from './components/PixelBlast';

function App() {
  return (
    <div className="relative min-h-screen z-0">
      <div className="fixed inset-0 z-[-1]">
        <PixelBlast
          style={{ width: '100%', height: '100%', position: 'absolute' }}
          variant="square"
          pixelSize={3}
          color="#00b37d"
          patternScale={2}
          patternDensity={1}
          enableRipples={true}
          rippleSpeed={0.3}
          rippleThickness={0.1}
          rippleIntensityScale={1}
          speed={0.5}
          transparent={true}
          edgeFade={0.5}
        />
      </div>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/index" element={<Landing />} />
          <Route path="/university" element={<University />} />
          <Route path="/university-issue" element={<UniversityIssue />} />
          <Route path="/university-revoke" element={<UniversityRevoke />} />
          <Route path="/student/:uid" element={<Student />} />
          <Route path="/student/login" element={<StudentLogin />} />
          <Route path="/student-login" element={<StudentLogin />} />
          <Route path="/university-login" element={<UniversityLogin />} />
          <Route path="/university/login" element={<UniversityLogin />} />
          <Route path="/universities/login" element={<UniversityLogin />} />
          <Route path="/employer" element={<Employer />} />
          <Route path="/verify" element={<Employer />} />
          <Route path="/verify-success" element={<VerifySuccess />} />
          <Route path="/verify-failed" element={<VerifyFailed />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
