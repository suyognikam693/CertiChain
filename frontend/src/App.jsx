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
import Dither from './components/Dither';

function App() {
  return (
    <div className="relative min-h-screen z-0">
      <div className="fixed inset-0 z-[-1]">
        <Dither
          waveColor={[16 / 255, 185 / 255, 129 / 255, 80 / 255]}
          baseColor={[18 / 255, 23 / 255, 32 / 255]}
          disableAnimation={false}
          enableMouseInteraction={true}
          mouseRadius={1}
          colorNum={5}
          waveAmplitude={0.1}
          waveFrequency={0.1}
          waveSpeed={1}
          pixelSize={2}
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
